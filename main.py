"""
中国語動画の自動翻訳・字幕生成（フェーズ1 CLI）

使い方:
    python main.py path/to/video.mp4
    python main.py path/to/video.mp4 --format srt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from auto_subtitle.config import AppConfig, GeminiConfig, WhisperConfig, load_config
from auto_subtitle.core import DEFAULT_GEMINI_MODEL
from auto_subtitle.pipeline import SubtitlePipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="中国語動画を認識・翻訳し、字幕ファイル（VTT/SRT）を生成します。",
    )
    parser.add_argument("input", type=Path, help="入力動画/音声ファイルのパス")
    parser.add_argument("--model", default="large-v3", help="Whisperモデル名")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("-f", "--format", choices=["vtt", "srt"], default="vtt")
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--gemini-model", default=None)
    parser.add_argument("--env", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.env:
        load_dotenv(args.env)
    else:
        load_dotenv()

    try:
        base_config = load_config(args.env)
    except ValueError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    gemini_model = args.gemini_model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    compute_type = args.compute_type
    if args.device == "cpu" and compute_type == "float16":
        compute_type = "int8"

    config = AppConfig(
        whisper=WhisperConfig(
            model=args.model,
            device=args.device,
            compute_type=compute_type,
        ),
        gemini=GeminiConfig(
            api_key=base_config.gemini.api_key,
            model=gemini_model,
        ),
        output_format=args.format,
    )

    input_path = args.input.resolve()
    output_path = args.output

    pipeline = SubtitlePipeline(config)

    try:
        print(f"処理開始: {input_path}")
        result = pipeline.run(input_path, output_path, subtitle_fmt=args.format)
    except FileNotFoundError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    out = output_path or input_path.with_suffix(f".{args.format}")
    print(f"\n完了: {out} ({len(result.segments)} セグメント)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
