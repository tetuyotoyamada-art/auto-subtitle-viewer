"""Command-line interface for auto-subtitle-viewer."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from auto_subtitle.config import load_config
from auto_subtitle.pipeline import SubtitlePipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-subtitle",
        description="動画の音声を認識し、中国語→日本語の字幕ファイルを生成します。",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="入力動画/音声ファイルのパス",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="出力字幕ファイルのパス（省略時は入力ファイルと同じ名前）",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["vtt", "srt"],
        default="vtt",
        help="出力形式（デフォルト: vtt）",
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=None,
        help=".env ファイルのパス",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="詳細ログを表示",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = load_config(args.env)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Inject CLI format override into config
    from dataclasses import replace

    config = replace(config, output_format=args.format)

    pipeline = SubtitlePipeline(config)

    try:
        output = pipeline.run(args.input, args.output)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logging.exception("Pipeline failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Done: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
