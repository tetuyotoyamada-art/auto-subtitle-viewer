"""Phase 1 core logic: transcribe, translate, and format subtitles."""

from __future__ import annotations

import logging
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from auto_subtitle.subtitle.models import SubtitleSegment
from auto_subtitle.subtitle.writers import format_subtitle_content

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

ProgressCallback = Callable[[str, str, int | None], None]

TRANSLATION_SYSTEM_PROMPT = """\
あなたは多言語動画の字幕翻訳・整形の専門家です。

入力されるテキストは、Whisper により自動認識された言語（日本語・韓国語・中国語・英語など）で書かれています。
原文がすでに日本語の場合も含め、タイムスタンプ付き字幕（SRTまたはVTT形式）を、
タイムスタンプの構造や行数を絶対に崩さずに、自然で読みやすい「日本語の字幕」として出力してください。

厳守事項:
- タイムスタンプ行（例: 00:00:01.000 --> 00:00:04.500）は一字一句変更しない
- ブロック数・空行の位置・行数を維持する（SRTの場合は番号行も維持）
- 字幕テキスト行のみを処理する（日本語への翻訳、または日本語としての意訳・整形）
- 原文が日本語以外の場合は、動画字幕として自然な日本語に意訳する（直訳より読みやすさを優先）
- 原文がすでに日本語の場合は、読みやすい字幕表現に整える（意味を変えない）
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
) -> tuple[list[SubtitleSegment], str | None]:
    if device == "cuda":
        setup_cuda_libs()

    from faster_whisper import WhisperModel

    if not media_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {media_path}")

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    # language を指定しないことで Whisper の自動言語認識を利用する
    segments_iter, info = model.transcribe(
        str(media_path),
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
    return segments, info.language


def segments_to_subtitle_text(segments: list[SubtitleSegment], fmt: str) -> str:
    """Combine all segments into a single VTT or SRT document (source language)."""
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


@dataclass(frozen=True)
class ParsedCue:
    start: float
    end: float
    text: str


_TIMESTAMP_PATTERN = r"\d{2}:\d{2}:\d{2}[.,]\d{3}"


def _timestamp_to_seconds(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    hours, minutes, seconds = ts.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _parse_vtt_cues(text: str) -> list[ParsedCue]:
    body = text
    if body.startswith("WEBVTT"):
        body = body.split("\n", 1)[1] if "\n" in body else ""

    pattern = re.compile(
        rf"({_TIMESTAMP_PATTERN})\s*-->\s*({_TIMESTAMP_PATTERN})\s*\n"
        rf"(.*?)(?=\n{_TIMESTAMP_PATTERN}\s*-->|\Z)",
        re.DOTALL,
    )
    return [
        ParsedCue(
            start=_timestamp_to_seconds(start_ts),
            end=_timestamp_to_seconds(end_ts),
            text=body_text.strip(),
        )
        for start_ts, end_ts, body_text in pattern.findall(body)
    ]


def _parse_srt_cues(text: str) -> list[ParsedCue]:
    pattern = re.compile(
        rf"\d+\s*\n({_TIMESTAMP_PATTERN})\s*-->\s*({_TIMESTAMP_PATTERN})\s*\n"
        rf"(.*?)(?=\n\d+\s*\n|\Z)",
        re.DOTALL,
    )
    return [
        ParsedCue(
            start=_timestamp_to_seconds(start_ts),
            end=_timestamp_to_seconds(end_ts),
            text=body_text.strip(),
        )
        for start_ts, end_ts, body_text in pattern.findall(text)
    ]


def _parse_vtt_blocks(text: str) -> list[str]:
    return [cue.text for cue in _parse_vtt_cues(text)]


def _parse_srt_blocks(text: str) -> list[str]:
    return [cue.text for cue in _parse_srt_cues(text)]


def _split_cue_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _align_translated_segments(
    segments: list[SubtitleSegment],
    cues: list[ParsedCue],
    *,
    tolerance: float = 0.35,
) -> int:
    """Match translated cues to source segments by timestamp and fallbacks."""
    used_cue_indices: set[int] = set()

    for seg in segments:
        best_index: int | None = None
        best_diff = float("inf")
        for index, cue in enumerate(cues):
            if index in used_cue_indices:
                continue
            diff = abs(cue.start - seg.start)
            if diff <= tolerance and diff < best_diff:
                best_diff = diff
                best_index = index
        if best_index is not None:
            seg.text_ja = cues[best_index].text
            used_cue_indices.add(best_index)

    for index, seg in enumerate(segments):
        if not seg.text_ja:
            continue
        lines = _split_cue_lines(seg.text_ja)
        if len(lines) <= 1:
            continue
        followers: list[SubtitleSegment] = []
        for follower in segments[index + 1 :]:
            if follower.text_ja:
                break
            followers.append(follower)
        if followers and len(lines) == len(followers) + 1:
            seg.text_ja = lines[0]
            for follower, line in zip(followers, lines[1:]):
                follower.text_ja = line

    unmatched_segments = [seg for seg in segments if not seg.text_ja]
    unused_cues = [cue for index, cue in enumerate(cues) if index not in used_cue_indices]

    for seg, cue in zip(unmatched_segments, unused_cues):
        seg.text_ja = cue.text

    remaining_segments = [seg for seg in segments if not seg.text_ja]
    remaining_cues = [
        cue for index, cue in enumerate(cues) if index not in used_cue_indices
    ][len(unmatched_segments) :]

    if remaining_segments and remaining_cues:
        for cue in remaining_cues:
            lines = _split_cue_lines(cue.text)
            if not lines:
                continue
            if len(lines) == len(remaining_segments):
                for seg, line in zip(remaining_segments, lines):
                    seg.text_ja = line
                break
            if len(lines) > len(remaining_segments):
                for seg, line in zip(remaining_segments, lines[-len(remaining_segments) :]):
                    seg.text_ja = line
                break

    for seg in segments:
        if not seg.text_ja:
            seg.text_ja = seg.text_zh

    return sum(1 for seg in segments if seg.text_ja)


def _log_segment_count_mismatch(
    *,
    source_count: int,
    translated_count: int,
    raw_response: str,
    fmt: str,
) -> None:
    """Emit debug output when Gemini translation segment counts do not match."""
    separator = "=" * 72
    header = "GEMINI TRANSLATION SEGMENT MISMATCH (DEBUG)"
    body = (
        f"\n{separator}\n"
        f"  {header}\n"
        f"{separator}\n"
        f"  原文のセグメント数          : {source_count}\n"
        f"  翻訳後のセグメント数        : {translated_count}\n"
        f"  字幕形式                    : {fmt.upper()}\n"
        f"{separator}\n"
        f"  Gemini 生レスポンス（パース前）:\n"
        f"{separator}\n"
        f"{raw_response}\n"
        f"{separator}\n"
    )

    print(body, flush=True)
    logger.error(
        "%s | source=%d translated=%d fmt=%s | raw_response=%r",
        header,
        source_count,
        translated_count,
        fmt,
        raw_response,
    )


def apply_translated_subtitle_text(
    segments: list[SubtitleSegment],
    translated_text: str,
    fmt: str,
) -> None:
    cleaned = _strip_markdown_fence(translated_text)
    cues = _parse_srt_cues(cleaned) if fmt == "srt" else _parse_vtt_cues(cleaned)
    texts = [cue.text for cue in cues]

    if len(texts) == len(segments):
        for seg, text_ja in zip(segments, texts):
            seg.text_ja = text_ja
        return

    _log_segment_count_mismatch(
        source_count=len(segments),
        translated_count=len(texts),
        raw_response=translated_text,
        fmt=fmt,
    )

    logger.warning(
        "Segment count mismatch (source=%d, translated=%d). "
        "Attempting timestamp-based realignment.",
        len(segments),
        len(texts),
    )
    print(
        f"[WARN] セグメント数不一致のためタイムスタンプ照合で復旧を試みます "
        f"(原文 {len(segments)} / 翻訳 {len(texts)})",
        flush=True,
    )

    _align_translated_segments(segments, cues)

    fallback_count = sum(1 for seg in segments if seg.text_ja == seg.text_zh)
    if fallback_count:
        logger.warning(
            "Used source text as fallback for %d segment(s) after realignment.",
            fallback_count,
        )
        print(
            f"[WARN] 復旧後も {fallback_count} セグメントは原文テキストで補完しました。",
            flush=True,
        )


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
            f"以下は{fmt_label}形式の字幕です（Whisper による自動言語認識の結果）。"
            f"原文の言語に関わらず、タイムスタンプの構造を維持したまま、"
            f"自然で読みやすい日本語の字幕として出力してください。\n\n"
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
    report("transcribing", "音声認識中（言語を自動検出）…")

    segments, detected_language = transcribe(
        media_path,
        model_name=opts.whisper_model,
        device=opts.device,
        compute_type=compute_type,
    )

    lang_label = detected_language or "不明"
    report(
        "transcribed",
        f"音声認識が完了しました（検出言語: {lang_label}、{len(segments)} セグメント）",
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
