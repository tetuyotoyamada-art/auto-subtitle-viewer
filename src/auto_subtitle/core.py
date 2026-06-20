"""Phase 1 core logic: transcribe, translate, and format subtitles."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from auto_subtitle.subtitle.models import SubtitleSegment
from auto_subtitle.subtitle.writers import format_subtitle_content

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

ProgressCallback = Callable[[str, str, int | None], None]

TRANSLATION_SYSTEM_PROMPT = """\
あなたは中国語動画の字幕翻訳者です。

以下のタイムスタンプ付きのテキスト（SRTまたはVTT形式）を、
タイムスタンプの構造や行数を絶対に崩さずに、中国語から自然な日本語に翻訳してそのまま出力してください。

厳守事項:
- タイムスタンプ行（例: 00:00:01.000 --> 00:00:04.500）は一字一句変更しない
- ブロック数・空行の位置・行数を維持する（SRTの場合は番号行も維持）
- 字幕テキスト行のみを中国語から日本語に翻訳する
- 動画の字幕として自然な日本語に意訳する（直訳より読みやすさを優先）
- 1行あたり長くなりすぎないよう短い表現を使う
- 説明・注釈・Markdownコードブロックは出力しない
- 翻訳後の字幕ファイルの内容のみを返す
"""


@dataclass(frozen=True)
class ProcessOptions:
    whisper_model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    subtitle_fmt: str = "vtt"
    gemini_model: str = DEFAULT_GEMINI_MODEL


@dataclass(frozen=True)
class ProcessResult:
    segments: list[SubtitleSegment]
    subtitle_content: str
    format: str


def setup_cuda_libs() -> None:
    """Register NVIDIA CUDA/cuDNN DLL directories for CTranslate2 on Windows."""
    if sys.platform == "win32":
        dll_subdir = "bin"
    else:
        dll_subdir = "lib"

    bin_dirs: list[str] = []
    seen: set[str] = set()

    def _add_dir(path: str) -> None:
        norm = os.path.normcase(os.path.normpath(path))
        if norm in seen or not os.path.isdir(path):
            return
        seen.add(norm)
        bin_dirs.append(path)

    for pkg_name in (
        "nvidia.cublas",
        "nvidia.cudnn",
        "nvidia.cuda_nvrtc",
        "nvidia.cuda_runtime",
    ):
        try:
            mod = __import__(pkg_name, fromlist=["__path__"])
        except ImportError:
            continue
        pkg_dir = next(iter(getattr(mod, "__path__", [])), None)
        if pkg_dir:
            _add_dir(os.path.join(pkg_dir, dll_subdir))

    site_packages = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if site_packages.is_dir():
        for pkg_dir in site_packages.iterdir():
            if pkg_dir.is_dir():
                _add_dir(str(pkg_dir / dll_subdir))

    if not bin_dirs:
        return

    if sys.platform == "win32":
        os.environ["PATH"] = os.pathsep.join(bin_dirs) + os.pathsep + os.environ.get("PATH", "")
        for directory in bin_dirs:
            try:
                os.add_dll_directory(directory)
            except (FileNotFoundError, OSError):
                pass
    else:
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            bin_dirs + ([existing] if existing else [])
        )


def format_timestamp(seconds: float, *, separator: str = ".") -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def transcribe(
    media_path: Path,
    *,
    model_name: str,
    device: str,
    compute_type: str,
) -> list[SubtitleSegment]:
    if device == "cuda":
        setup_cuda_libs()

    from faster_whisper import WhisperModel

    if not media_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {media_path}")

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments_iter, _info = model.transcribe(
        str(media_path),
        language="zh",
        vad_filter=True,
    )

    segments: list[SubtitleSegment] = []
    for index, segment in enumerate(segments_iter, start=1):
        segments.append(
            SubtitleSegment(
                index=index,
                start=segment.start,
                end=segment.end,
                text_zh=segment.text.strip(),
            )
        )
    return segments


def segments_to_subtitle_text(segments: list[SubtitleSegment], fmt: str) -> str:
    """Combine all segments into a single VTT or SRT document (Chinese source)."""
    if fmt == "srt":
        lines: list[str] = []
        for seg in segments:
            start = format_timestamp(seg.start, separator=",")
            end = format_timestamp(seg.end, separator=",")
            lines.append(str(seg.index))
            lines.append(f"{start} --> {end}")
            lines.append(seg.text_zh)
            lines.append("")
        return "\n".join(lines)

    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp(seg.start, separator=".")
        end = format_timestamp(seg.end, separator=".")
        lines.append(f"{start} --> {end}")
        lines.append(seg.text_zh)
        lines.append("")
    return "\n".join(lines)


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_vtt_blocks(text: str) -> list[str]:
    body = text
    if body.startswith("WEBVTT"):
        body = body.split("\n", 1)[1] if "\n" in body else ""

    pattern = re.compile(
        r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*\n(.*?)(?=\n\d{2}:\d{2}:\d{2}\.\d{3}\s*-->|\Z)",
        re.DOTALL,
    )
    return [match.strip() for match in pattern.findall(body)]


def _parse_srt_blocks(text: str) -> list[str]:
    pattern = re.compile(
        r"\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*\n(.*?)(?=\n\d+\s*\n|\Z)",
        re.DOTALL,
    )
    return [match.strip() for match in pattern.findall(text)]


def apply_translated_subtitle_text(
    segments: list[SubtitleSegment],
    translated_text: str,
    fmt: str,
) -> None:
    cleaned = _strip_markdown_fence(translated_text)
    texts = _parse_srt_blocks(cleaned) if fmt == "srt" else _parse_vtt_blocks(cleaned)

    if len(texts) != len(segments):
        raise ValueError(
            f"翻訳結果のセグメント数 ({len(texts)}) が原文 ({len(segments)}) と一致しません。"
            "Geminiの出力形式が崩れた可能性があります。"
        )

    for seg, text_ja in zip(segments, texts):
        seg.text_ja = text_ja


def translate_segments(
    segments: list[SubtitleSegment],
    *,
    api_key: str,
    model_name: str,
    subtitle_fmt: str = "vtt",
) -> list[SubtitleSegment]:
    from google import genai
    from google.genai import types

    if not segments:
        return segments

    client = genai.Client(api_key=api_key)
    source_text = segments_to_subtitle_text(segments, subtitle_fmt)
    fmt_label = subtitle_fmt.upper()

    response = client.models.generate_content(
        model=model_name,
        contents=(
            f"以下は{fmt_label}形式の中国語字幕です。"
            f"タイムスタンプの構造を維持したまま、日本語に翻訳してください。\n\n"
            f"{source_text}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=TRANSLATION_SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )

    apply_translated_subtitle_text(segments, response.text or "", subtitle_fmt)
    return segments


def process_media(
    media_path: Path,
    *,
    api_key: str,
    options: ProcessOptions | None = None,
    on_progress: ProgressCallback | None = None,
) -> ProcessResult:
    """Run the full pipeline: transcribe -> translate -> format subtitle content."""

    def report(stage: str, message: str, segment_count: int | None = None) -> None:
        if on_progress:
            on_progress(stage, message, segment_count)

    opts = options or ProcessOptions()
    compute_type = opts.compute_type
    if opts.device == "cpu" and compute_type == "float16":
        compute_type = "int8"

    report("preparing", "処理を準備しています…")
    report("transcribing", "音声認識中（faster-whisper）…")

    segments = transcribe(
        media_path,
        model_name=opts.whisper_model,
        device=opts.device,
        compute_type=compute_type,
    )

    report(
        "transcribed",
        f"音声認識が完了しました（{len(segments)} セグメント）",
        len(segments),
    )
    report("translating", "Gemini で日本語翻訳中…")

    segments = translate_segments(
        segments,
        api_key=api_key,
        model_name=opts.gemini_model,
        subtitle_fmt=opts.subtitle_fmt,
    )

    report("formatting", "字幕ファイルを整形中…")
    content = format_subtitle_content(segments, opts.subtitle_fmt)
    report("complete", "字幕生成が完了しました", len(segments))

    return ProcessResult(
        segments=segments,
        subtitle_content=content,
        format=opts.subtitle_fmt,
    )
