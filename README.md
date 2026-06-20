# Auto Subtitle Viewer

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

**Whisper** と **Google Gemini** を組み合わせ、動画・音声から **日本語字幕** を自動生成する **ローカル完結型** の Web アプリケーションです。

日本語・韓国語・中国語・英語など **多言語の音声を自動認識** し、自然な日本語字幕（WebVTT / SRT）に変換します。動画をドラッグ＆ドロップするだけで、音声認識 → 翻訳 → 再生・表示までをブラウザ上で完結できます。

バックエンドとフロントエンドは **1 つのサーバー（ポート 8000）** に統合されており、`run_app.bat` のダブルクリックで起動できます。

---

## 主な機能

- **ドラッグ＆ドロップ** — 動画・音声ファイル（MP4, MKV, WebM, MOV, WAV など）をドロップするだけで処理開始
- **多言語対応** — Whisper の自動言語認識（言語指定なし）で入力言語を判別
- **リアルタイム進捗表示** — 「音声認識中」「翻訳中」など、処理ステップを SSE で逐次表示
- **日本語字幕オーバーレイ** — 動画プレイヤー上にタイミング同期された字幕を表示
- **字幕カスタマイズ** — フォントサイズ・文字色を UI から変更（設定は `localStorage` に保存）
- **字幕パネル** — 認識原文と日本語訳をセグメント単位で一覧表示・シーク操作
- **字幕ダウンロード** — WebVTT / SRT 形式でファイル出力
- **ワンクリック起動** — `run_app.bat` でサーバー起動とブラウザ表示を自動化
- **エラーハンドリング** — API エラーを分かりやすい日本語メッセージで表示、再試行ボタン付き
- **翻訳結果の復旧** — Gemini 出力のセグメント数不一致時、タイムスタンプ照合で自動復旧

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| **音声認識** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2 / CUDA 対応、自動言語認識） |
| **翻訳** | [Google Gemini API](https://ai.google.dev/)（`google-genai` SDK、`gemini-2.5-flash`） |
| **バックエンド** | Python 3.10+, FastAPI, Uvicorn |
| **フロントエンド** | React 19, TypeScript, Vite |
| **配信** | FastAPI による静的ファイル配信（`frontend/dist/`） |

---

## 前提条件

| 項目 | 内容 |
|---|---|
| **OS** | Windows 10 / 11（ワンクリック起動バッチは Windows 向け） |
| **Python** | 3.10 以上 |
| **Node.js** | 18 以上（フロントエンドビルド時のみ） |
| **Gemini API キー** | [Google AI Studio](https://aistudio.google.com/apikey) で無料取得 |
| **GPU（推奨）** | NVIDIA GPU + CUDA 12 対応ドライバ（CPU でも動作可能） |
| **FFmpeg** | faster-whisper / PyAV が内部利用（別途インストール不要な場合が多い） |

---

## セットアップ

### 1. リポジトリの取得

```sh
git clone <repository-url>
cd auto-subtitle-viewer
```

### 2. Python 仮想環境の作成

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

### 3. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、API キーを設定します。

```bat
copy .env.example .env
```

`.env` の例:

```env
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.5-flash
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

| 変数名 | 必須 | 説明 |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API キー |
| `GEMINI_MODEL` | — | 使用モデル（デフォルト: `gemini-2.5-flash`） |
| `WHISPER_MODEL` | — | Whisper モデル（デフォルト: `large-v3`） |
| `WHISPER_DEVICE` | — | `cuda` または `cpu` |
| `WHISPER_COMPUTE_TYPE` | — | `float16`（GPU）/ `int8`（CPU 推奨） |

---

## 起動方法

### フロントエンドのビルド（初回・UI 変更時）

```bat
build_frontend.bat
```

内部で `frontend/` ディレクトリに移動し、`npm install`（初回）と `npm run build` を実行します。  
成果物は `frontend/dist/` に出力されます。

手動で行う場合:

```sh
cd frontend
npm install
npm run build
```

### アプリの起動（ワンクリック）

```bat
run_app.bat
```

`run_app.bat` をダブルクリックすると、以下が **自動で** 実行されます。

1. フロントエンド未ビルド時は `build_frontend.bat` を実行
2. Python 仮想環境（`.venv`）を有効化
3. ブラウザで http://127.0.0.1:8000 を開く
4. 統合 FastAPI サーバーを起動

> **Tip:** ブラウザが先に開くため、サーバー起動直後は一瞬「接続できない」場合があります。数秒待って再読み込みしてください。

### 開発モード（フロントエンド）

UI をホットリロードしながら開発する場合は、バックエンドとフロントエンドを別々に起動します。

```bat
REM ターミナル 1: API サーバー
.venv\Scripts\activate.bat
uvicorn auto_subtitle.api.app:app --host 127.0.0.1 --port 8000 --reload
```

```sh
# ターミナル 2: Vite 開発サーバー（/api を :8000 にプロキシ）
cd frontend
npm run dev
```

ブラウザは http://127.0.0.1:5173 を開いてください。

---

## プロジェクト構成

```
auto-subtitle-viewer/
├── run_app.bat              # ワンクリック起動
├── build_frontend.bat       # フロントエンドビルド
├── main.py                  # CLI エントリポイント（任意）
├── requirements.txt
├── .env.example
├── frontend/                # React + Vite フロントエンド
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/client.ts    # API クライアント（SSE 対応）
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── SubtitleOverlay.tsx
│   │   │   ├── SubtitlePanel.tsx
│   │   │   ├── SubtitleSettings.tsx
│   │   │   ├── ProgressStepper.tsx
│   │   │   └── ErrorAlert.tsx
│   │   └── utils/
│   └── dist/                # ビルド成果物（FastAPI が配信）
└── src/auto_subtitle/       # Python パッケージ
    ├── core.py              # 音声認識・翻訳・字幕復旧ロジック
    ├── config.py            # 環境変数・Whisper / Gemini 設定
    ├── pipeline.py
    └── api/
        ├── app.py           # FastAPI（API + 静的配信）
        ├── routes.py        # REST / SSE エンドポイント
        └── schemas.py
```

---

## 処理フロー

```
動画・音声アップロード
    ↓
faster-whisper（自動言語認識 + タイムスタンプ付き文字起こし）
    ↓
Google Gemini（日本語字幕への翻訳・一括リクエスト）
    ↓
WebVTT / SRT 字幕生成
    ↓
ブラウザで再生・オーバーレイ表示・ダウンロード
```

### 進捗ステージ（SSE）

| ステージ | 内容 |
|---|---|
| `preparing` | 一時ファイル保存・オプション構築 |
| `transcribing` | Whisper による音声認識 |
| `transcribed` | 認識完了（セグメント数を通知） |
| `translating` | Gemini による一括翻訳 |
| `formatting` | 字幕ファイル整形 |
| `complete` | 完了 |

---

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/api/health` | サーバー稼働確認 |
| `POST` | `/api/subtitles/generate` | ファイルアップロード → 字幕生成（一括レスポンス） |
| `POST` | `/api/subtitles/generate-stream` | ファイルアップロード → SSE で進捗付き字幕生成 |
| `POST` | `/api/subtitles/generate-path` | サーバー上のファイルパス指定（ローカル開発用） |

Web UI は `generate-stream` を使用し、リアルタイムで進捗を表示します。

---

## CLI での利用（任意）

Web UI 以外に、コマンドラインからも字幕ファイルを生成できます。

```bat
.venv\Scripts\activate.bat
python main.py path\to\video.mp4
python main.py path\to\video.mp4 --format srt
python main.py path\to\video.mp4 --device cpu --compute-type int8
```

---

## 注意事項

- **初回の Whisper モデルダウンロード**  
  `large-v3` などのモデルは初回実行時に Hugging Face から自動ダウンロードされます。数 GB 規模のため、**ネットワーク環境によっては 10 分以上** かかることがあります。

- **GPU 利用（Windows）**  
  CUDA 12 用の NVIDIA パッケージ（`nvidia-cublas-cu12` 等）が `requirements.txt` に含まれています。GPU がない場合は `.env` で `WHISPER_DEVICE=cpu` と `WHISPER_COMPUTE_TYPE=int8` を指定してください。

- **Gemini API レート制限**  
  無料枠には 1 分あたりのリクエスト上限があります。本ツールは翻訳を **1 リクエストにまとめる** 設計のため、通常は問題になりにくいですが、429 エラー時は 1〜2 分待ってから再試行してください。

- **処理時間**  
  動画の長さ・GPU 性能・モデルサイズによって、数分〜十数分かかる場合があります。進捗ステッパーで現在のステップを確認できます。

- **Gemini 翻訳出力のずれ**  
  まれに Gemini がセグメント数を一致させられない場合があります（末尾の結合・タイムスタンプの誤りなど）。その場合、コンソールに `GEMINI TRANSLATION SEGMENT MISMATCH (DEBUG)` が出力され、**タイムスタンプ照合による自動復旧** が試みられます。復旧できないセグメントは認識原文で補完されます。

- **`.env` は Git に含めない**  
  API キーを含む `.env` は `.gitignore` 済みです。共有・コミットしないでください。

---

## ライセンス

MIT License
