# Auto Subtitle Viewer

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

**Whisper** と **Google Gemini** を組み合わせ、中国語動画から日本語字幕を自動生成する **ローカル完結型** の Web アプリケーションです。

動画をドラッグ＆ドロップするだけで、音声認識 → 翻訳 → 字幕表示までをブラウザ上で完結できます。バックエンドとフロントエンドは **1 つのサーバー（ポート 8000）** に統合されており、`run_app.bat` のダブルクリックで起動できます。

---

## 主な機能

- **ドラッグ＆ドロップ** — 動画ファイルをドロップするだけで処理開始
- **リアルタイム進捗表示** — 「音声認識中」「翻訳中」など、処理ステップを SSE で逐次表示
- **日本語字幕オーバーレイ** — 動画プレイヤー上にタイミング同期された字幕を表示
- **字幕カスタマイズ** — フォントサイズ・文字色を UI から変更（設定はブラウザに保存）
- **字幕パネル** — 中国語原文と日本語訳をセグメント単位で一覧表示・シーク操作
- **字幕ダウンロード** — WebVTT / SRT 形式でファイル出力
- **ワンクリック起動** — `run_app.bat` でサーバー起動とブラウザ表示を自動化
- **エラーハンドリング** — API エラーを分かりやすい日本語メッセージで表示、再試行ボタン付き

---

## 技術スタック

| レイヤー | 技術 |
|---|---|
| **音声認識** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2 / CUDA 対応） |
| **翻訳** | [Google Gemini API](https://ai.google.dev/)（`google-genai` SDK） |
| **バックエンド** | Python 3.10+, FastAPI, Uvicorn |
| **フロントエンド** | React, TypeScript, Vite |
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
```

| 変数名 | 必須 | 説明 |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini API キー |
| `GEMINI_MODEL` | — | 使用モデル（デフォルト: `gemini-2.5-flash`） |
| `WHISPER_MODEL` | — | Whisper モデル（デフォルト: `large-v3`） |
| `WHISPER_DEVICE` | — | `cuda` または `cpu` |

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
│   └── dist/                # ビルド成果物（FastAPI が配信）
└── src/auto_subtitle/       # Python パッケージ
    ├── core.py              # 音声認識・翻訳コア
    ├── pipeline.py
    └── api/
        ├── app.py           # FastAPI（API + 静的配信）
        └── routes.py
```

---

## 処理フロー

```
動画アップロード
    ↓
faster-whisper（中国語音声認識 + タイムスタンプ）
    ↓
Google Gemini（日本語翻訳・一括リクエスト）
    ↓
WebVTT / SRT 字幕生成
    ↓
ブラウザで再生・表示・ダウンロード
```

---

## CLI での利用（任意）

Web UI 以外に、コマンドラインからも字幕ファイルを生成できます。

```bat
.venv\Scripts\activate.bat
python main.py path\to\video.mp4
python main.py path\to\video.mp4 --format srt
```

---

## 注意事項

- **初回の Whisper モデルダウンロード**  
  `large-v3` などのモデルは初回実行時に Hugging Face から自動ダウンロードされます。数 GB 規模のため、**ネットワーク環境によっては 10 分以上** かかることがあります。

- **GPU 利用（Windows）**  
  CUDA 12 用の NVIDIA パッケージ（`nvidia-cublas-cu12` 等）が `requirements.txt` に含まれています。GPU がない場合は `.env` で `WHISPER_DEVICE=cpu` を指定するか、API リクエスト時に CPU を選択してください。

- **Gemini API レート制限**  
  無料枠には 1 分あたりのリクエスト上限があります。本ツールは翻訳を **1 リクエストにまとめる** 設計のため、通常は問題になりにくいですが、429 エラー時は 1〜2 分待ってから再試行してください。

- **処理時間**  
  動画の長さ・GPU 性能・モデルサイズによって、数分〜十数分かかる場合があります。進捗バーで現在のステップを確認できます。

- **`.env` は Git に含めない**  
  API キーを含む `.env` は `.gitignore` 済みです。共有・コミットしないでください。

---

## ライセンス

MIT License
