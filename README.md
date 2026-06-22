# Auto Subtitle Viewer

<img src="demo.gif" alt="Demo" width="40%">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

**Whisper** と **Google Gemini** を組み合わせ、動画・音声から **日本語字幕** を自動生成する **ローカル完結型** の Web アプリケーションです。

日本語・韓国語・中国語・英語など **多言語の音声を自動認識** し、自然な日本語字幕（WebVTT / SRT）に変換します。動画をドラッグ＆ドロップするだけで、音声認識 → 翻訳 → 再生・表示 → 字幕付き MP4 のダウンロードまでをブラウザ上で完結できます。

バックエンドとフロントエンドは **1 つのサーバー（ポート 8000）** に統合されており、Windows では `setup.bat` → `run_app.bat` で起動できます。

> **Demo GIF:** リポジトリ直下に `demo.gif` を配置すると上記プレースホルダーが表示されます。

---

## クイックスタート（Windows）

```bat
git clone https://github.com/<your-org>/auto-subtitle-viewer.git
cd auto-subtitle-viewer
setup.bat
```

1. `setup.bat` が `.venv` 作成・依存関係インストール・フロントエンドビルド・`.env` 作成を行います
2. `.env` を開き **`GEMINI_API_KEY`** を設定（[Google AI Studio](https://aistudio.google.com/apikey) で無料取得）
3. 必要なら Whisper 設定を PC に合わせて変更（後述）
4. `run_app.bat` を実行 → ブラウザで http://127.0.0.1:8000

---

## 主な機能

- **ドラッグ＆ドロップ** — 動画・音声ファイル（MP4, MKV, WebM, MOV, WAV など）をドロップするだけで処理開始
- **多言語対応** — faster-whisper の自動言語認識（言語指定なし）で入力言語を判別
- **Gemini JSON 一括翻訳** — **1 本の動画につき API リクエスト 1 回**（無料枠の節約）
- **リアルタイム進捗表示** — 「音声認識中」「翻訳中」など、処理ステップを SSE で逐次表示
- **日本語字幕オーバーレイ** — 動画プレイヤー上にタイミング同期された字幕を表示
- **字幕カスタマイズ** — フォントサイズ・文字色を UI から変更（設定は `localStorage` に保存）
- **字幕パネル** — 認識原文と日本語訳をセグメント単位で一覧表示・シーク操作
- **字幕ファイルダウンロード** — WebVTT / SRT 形式で出力
- **字幕付き MP4 ダウンロード（ハードサブ）** — FFmpeg で字幕を動画に焼き付け
- **PC ごとの Whisper 設定** — `.env` を切り替えるだけで CPU / GPU・モデルサイズを変更（Web UI が `/api/config` から自動取得）
- **エラーハンドリング** — API エラーを分かりやすい日本語メッセージで表示、再試行ボタン付き

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| **音声認識** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2 / CUDA 対応、自動言語認識） |
| **翻訳** | [Google Gemini API](https://ai.google.dev/)（`google-genai` SDK、`gemini-2.5-flash`） |
| **ハードサブ** | FFmpeg / ffprobe（ASS 字幕焼き付け、システム PATH に必要） |
| **バックエンド** | Python 3.10+, FastAPI, Uvicorn |
| **フロントエンド** | React 19, TypeScript, Vite |
| **配信** | FastAPI による静的ファイル配信（`frontend/dist/`） |

---

## 前提条件

| 項目 | 内容 |
|---|---|
| **OS** | Windows 10 / 11 推奨（`setup.bat` / `run_app.bat` は Windows 向け）。macOS / Linux も CLI・手動起動で利用可 |
| **Python** | 3.10 以上（Microsoft Store 版でも可。仮想環境 `.venv` の利用を推奨） |
| **Node.js** | 18 以上（`setup.bat` / `build_frontend.bat` でフロントエンドビルド時に必要） |
| **Gemini API キー** | [Google AI Studio](https://aistudio.google.com/apikey) で無料取得 |
| **FFmpeg** | **字幕付き MP4 ダウンロードに必須**（`ffmpeg` / `ffprobe` が PATH にあること） |
| **GPU（任意）** | NVIDIA GPU + CUDA 12 対応ドライバ（535 以降推奨）。**CPU のみでも動作** |

---

## セットアップ

### Windows（推奨）

```bat
setup.bat
```

`setup.bat` が以下を自動実行します。

| ステップ | 内容 |
|---|---|
| 1 | `.venv` 仮想環境の作成 |
| 2 | `pip install -r requirements.txt` と `pip install -e .` |
| 3 | `.env.example` → `.env` のコピー（未作成時） |
| 4 | `build_frontend.bat`（Node.js がある場合） |

### 手動セットアップ（macOS / Linux / Windows）

```sh
python3 -m venv .venv
source .venv/bin/activate          # Windows cmd: .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
cp .env.example .env               # Windows: copy .env.example .env
cd frontend && npm install && npm run build && cd ..
```

### FFmpeg（ハードサブ利用時）

```bat
REM Windows
winget install Gyan.FFmpeg
```

```sh
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### GPU 用パッケージ（任意）

CUDA 12 + 最新 NVIDIA ドライバがある PC のみ:

```bat
.venv\Scripts\activate.bat
pip install -r requirements-cuda.txt
```

`.env` で GPU 設定に切り替え:

```env
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

---

## 環境変数（`.env`）

**各 PC で `.env` だけ変えれば、コード変更なしで Whisper 設定を切り替えられます。** Web UI は起動時に `GET /api/config` で設定を取得します。

`.env.example` をコピーして `.env` を作成し、API キーを設定してください。

| 変数名 | 必須 | 説明 |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API キー |
| `GEMINI_MODEL` | — | 使用モデル（デフォルト: `gemini-2.5-flash`） |
| `WHISPER_MODEL` | — | Whisper モデル（下表参照） |
| `WHISPER_DEVICE` | — | `cuda` または `cpu` |
| `WHISPER_COMPUTE_TYPE` | — | `float16`（GPU）/ `int8`（CPU 推奨） |

### Whisper モデルと PC 設定の目安

| プロファイル | `.env` の例 | 向いている環境 |
|---|---|---|
| **CPU・初回お試し（推奨）** | `base` / `cpu` / `int8` | GPU なし、ドライバが古い、とにかく早く試したい |
| **CPU・高精度** | `medium` / `cpu` / `int8` | 時間はかかるが精度を上げたい |
| **GPU・高精度** | `large-v3` / `cuda` / `float16` | CUDA 12 + 最新 NVIDIA ドライバ + `requirements-cuda.txt` 済み |

> **Tip:** `.env.example` のデフォルトは **CPU + `base`** です。GPU PC ではコメント内の GPU ブロックに差し替えてください。

CUDA が `.env` で `cuda` でもドライバが使えない場合、サーバーは **自動的に CPU にフォールバック** します。

---

## 起動方法

### アプリの起動（Windows）

```bat
run_app.bat
```

`run_app.bat` の動作:

1. `.venv` と `.env` の存在を確認
2. `uvicorn` が `.venv` にインストールされているか確認
3. フロントエンド未ビルド時は `build_frontend.bat` を実行
4. ブラウザで http://127.0.0.1:8000 を開く
5. `python -m uvicorn ...` でサーバー起動

> **Tip:** ブラウザが先に開くため、起動直後は一瞬「接続できない」場合があります。数秒待って再読み込みしてください。

### 手動起動（macOS / Linux / 開発者向け）

```sh
source .venv/bin/activate
python -m uvicorn auto_subtitle.api.app:app --host 127.0.0.1 --port 8000
```

### 開発モード（フロントエンド）

```bat
REM ターミナル 1: API サーバー
.venv\Scripts\activate.bat
python -m uvicorn auto_subtitle.api.app:app --host 127.0.0.1 --port 8000 --reload
```

```sh
# ターミナル 2: Vite 開発サーバー
cd frontend
npm run dev
```

ブラウザは http://127.0.0.1:5173 を開いてください（`/api` は :8000 にプロキシ）。

### フロントエンドの再ビルド（UI 変更時）

```bat
build_frontend.bat
```

---

## プロジェクト構成

```
auto-subtitle-viewer/
├── setup.bat                # 初回セットアップ（venv / pip / .env / ビルド）
├── run_app.bat              # アプリ起動（Windows）
├── build_frontend.bat       # フロントエンドビルド
├── requirements.txt         # Python 依存（CPU でも可）
├── requirements-cuda.txt    # 任意: NVIDIA CUDA 12 パッケージ
├── main.py                  # CLI エントリポイント
├── .env.example             # 環境変数テンプレート（PC ごとに .env を作成）
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/client.ts    # /api/config 取得 + SSE
│   │   └── components/
│   └── dist/                # ビルド成果物（.gitignore、FastAPI が配信）
└── src/auto_subtitle/
    ├── config.py            # .env 読み込み + CUDA フォールバック
    ├── core.py
    └── api/
        ├── app.py
        ├── routes.py        # /api/config, 字幕生成 API
        └── schemas.py
```

---

## 処理フロー

```
動画・音声アップロード
    ↓
GET /api/config で .env の Whisper 設定を取得（Web UI）
    ↓
faster-whisper（自動言語認識 + タイムスタンプ付き文字起こし）
    ↓
Google Gemini（JSON 一括翻訳 → 日本語字幕、1 動画 = 1 API 呼び出し）
    ↓
WebVTT / SRT 字幕生成
    ↓
ブラウザで再生・オーバーレイ表示・字幕ファイル DL
    ↓
（任意）FFmpeg で ASS ハードサブ → 字幕付き MP4 ダウンロード
```

---

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/health` | サーバー稼働確認 |
| `GET` | `/api/config` | `.env` の Whisper 設定（解決済み device / model / compute_type） |
| `POST` | `/api/subtitles/generate` | ファイルアップロード → 字幕生成（一括レスポンス） |
| `POST` | `/api/subtitles/generate-stream` | SSE で進捗付き字幕生成（Web UI が使用） |
| `POST` | `/api/subtitles/generate-path` | サーバー上のファイルパス指定（ローカル開発用） |
| `POST` | `/api/download-video` | 動画 + セグメント JSON → 字幕焼き付け済み MP4 |

---

## CLI での利用（任意）

Web UI 以外に、コマンドラインからも字幕ファイルを生成できます。`.env` の設定がデフォルトとして使われます。

```bat
.venv\Scripts\activate.bat
python main.py path\to\video.mp4
python main.py path\to\video.mp4 --format srt
python main.py path\to\video.mp4 --device cpu --compute-type int8 --model base
```

---

## YouTube などから動画を取得する場合（任意）

本アプリに **yt-dlp は同梱されていません**。Creative Commons 動画などを YouTube から取得する場合は、別途 yt-dlp を使い、**ダウンロードしたファイルを Web UI にアップロード** してください。

```powershell
# PowerShell（Cursor ターミナル）— 仮想環境を有効化してから
.venv\Scripts\Activate.ps1
pip install yt-dlp
python -m yt_dlp -f "bestvideo+bestaudio/best" --merge-output-format mp4 "https://www.youtube.com/watch?v=VIDEO_ID"
```

> **注意:** PowerShell では `activate.bat` ではなく **`Activate.ps1`** を使ってください。`activate.bat` は cmd 用で、PowerShell から実行しても現在のシェルには反映されません。

---

## トラブルシューティング

### `'uvicorn' is not recognized` / 依存関係が入っていない

**原因:** `.venv` はあるが `pip install` していない、または仮想環境が有効化されていない。

**対処:**

```bat
setup.bat
```

または:

```bat
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

`run_app.bat` は `python -m uvicorn` を使うため、`uvicorn` コマンド自体が PATH になくても動作します。

---

### PowerShell で `pip install` しても `(.venv)` が付かない

**原因:** `activate.bat` は cmd 専用。PowerShell から実行しても別プロセスで終わるだけです。

**対処:**

```powershell
.venv\Scripts\Activate.ps1
pip -V   # → ...\.venv\... と表示されれば OK
```

実行ポリシーエラー時:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

確実な方法（有効化不要）:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

### `CUDA driver version is insufficient for CUDA runtime version`

**原因:** `.env` で `WHISPER_DEVICE=cuda` だが、NVIDIA ドライバが CUDA 12 ランタイムに追いついていない。

**対処（いずれか）:**

1. **CPU モード（すぐ試せる）** — `.env` を変更:

   ```env
   WHISPER_DEVICE=cpu
   WHISPER_COMPUTE_TYPE=int8
   WHISPER_MODEL=base
   ```

   `run_app.bat` を再起動。http://127.0.0.1:8000/api/config で `whisper_device: "cpu"` を確認。

2. **GPU を使う** — [NVIDIA ドライバ](https://www.nvidia.com/Download/index.aspx) を最新に更新 → PC 再起動 → `pip install -r requirements-cuda.txt`

---

### アップロード後、ブラウザが「音声認識中」のまま長時間止まる

**原因:** 初回実行時に Whisper モデルを Hugging Face からダウンロード中（`large-v3` は約 3GB）。UI はダウンロード中の進捗を表示しません。

**対処:**

- 初回は **15〜30 分以上** かかることがあります（タスクマネージャーで `python.exe` のネットワーク/ディスクを確認）
- 急ぐ場合は `.env` で `WHISPER_MODEL=base` に変更（約 150MB、かなり速い）
- 2 回目以降はキャッシュから読み込むため大幅に短縮

---

### `yt-dlp` コマンドが見つからない

**原因:** `pip install yt-dlp` がグローバル Python に入り、PATH 外の `Scripts` に配置された。

**対処:** モジュールとして実行（ハイフンではなくアンダースコア）:

```powershell
python -m yt_dlp "URL"
```

---

### 字幕付き MP4 が 503 エラー

**原因:** FFmpeg が PATH にない。

**対処:** `winget install Gyan.FFmpeg` などでインストール後、ターミナルを再起動。

---

### Gemini API 429 エラー

無料枠のレート制限です。1〜2 分待って再試行してください。本ツールは **1 動画 = 1 API リクエスト** のため、セグメント数に比例してクォータを消費しません。

---

## 注意事項

- **`.env` は Git に含めない** — API キーを含むため `.gitignore` 済みです。
- **処理時間** — 動画の長さ・モデルサイズ・CPU/GPU によって数分〜数十分かかります。CPU + `base` が最も手軽です。
- **Gemini 翻訳出力のずれ** — まれにセグメント数不一致が起きますが、タイムスタンプ照合による自動復旧を試みます。

---

## ライセンス

MIT License
