"""Phase 1 core logic: transcribe, translate, and format subtitles."""

from __future__ import annotations

import json
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

入力は Whisper により自動認識された字幕セグメントの JSON です（1動画分を1リクエストで処理します）。
segments 配列の各要素について、text フィールドの内容のみを自然で読みやすい日本語（text_ja）に翻訳・整形してください。

厳守事項:
- 1回のレスポンスですべてのセグメントを返す（セグメントごとの分割出力は禁止）
- index / start / end は入力値をそのまま維持する
- segments 配列の要素数は入力と同じ件数を維持する
- 原文が日本語以外の場合は、動画字幕として自然な日本語に意訳する
- 原文がすでに日本語の場合は、読みやすい字幕表現に整える（意味を変えない）
- 1行あたり長くなりすぎないよう短い表現を使う
- 説明・注釈・Markdownコードブロックは出力しない
- 出力は JSON のみ（形式は入力と同じ segments 配列構造）
"""

TRANSLATION_USER_PROMPT = """\
以下の JSON は1本の動画から得られた全字幕セグメントです。
segments 配列の各 text を text_ja に翻訳し、同じ構造の JSON だけを返してください。

出力形式（例）:
{{
  "segment_count": 2,
  "segments": [
    {{"index": 1, "start": 0.0, "end": 1.5, "text_ja": "..."}},
    {{"index": 2, "start": 1.5, "end": 3.0, "text_ja": "..."}}
  ]
}}

入力 JSON:
{payload}
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


def segments_to_translation_json(segments: list[SubtitleSegment]) -> str:
    """Serialize all segments into one JSON payload for a single batch API call."""
    payload = {
        "segment_count": len(segments),
        "segments": [
            {
                "index": seg.index,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text_zh,
            }
            for seg in segments
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _extract_json_object(text: str) -> str:
    cleaned = _strip_markdown_fence(text.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def apply_translated_json(segments: list[SubtitleSegment], raw_response: str) -> int:
    """Apply batch JSON translation by segment index. Returns number of segments filled."""
    try:
        parsed = json.loads(_extract_json_object(raw_response))
    except json.JSONDecodeError:
        logger.warning("Failed to parse Gemini response as JSON.")
        return 0

    items: list[object]
    if isinstance(parsed, dict):
        raw_items = parsed.get("segments", [])
        items = raw_items if isinstance(raw_items, list) else []
    elif isinstance(parsed, list):
        items = parsed
    else:
        return 0

    by_index = {seg.index: seg for seg in segments}
    matched = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        if not isinstance(index, int) or index not in by_index:
            continue
        text_ja = item.get("text_ja") or item.get("text")
        if not isinstance(text_ja, str) or not text_ja.strip():
            continue
        by_index[index].text_ja = _sanitize_cue_text(text_ja)
        matched += 1

    return matched


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
_ARROW_LINE = re.compile(
    rf"^\s*(?:{_TIMESTAMP_PATTERN}|\d{{4}}:\d{{2}}[.,]\d{{3}})\s*-->\s*"
    rf"(?:{_TIMESTAMP_PATTERN}|\d{{2}}:\d{{2}}:\d{{2}}[.,]\d{{3}})\s*$"
)


def _timestamp_to_seconds(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    hours, minutes, seconds = ts.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _normalize_malformed_vtt_timestamps(text: str) -> str:
    """Fix common Gemini typos such as ``0002:24.520 --> ...``."""

    def fix_line(line: str) -> str:
        stripped = line.strip()
        match = re.match(
            rf"^(\d{{4}}):(\d{{2}}[.,]\d{{3}})\s*-->\s*({_TIMESTAMP_PATTERN})\s*$",
            stripped,
        )
        if not match:
            return line
        hours, minutes = match.group(1)[:2], match.group(1)[2:]
        return f"{hours}:{minutes}:{match.group(2)} --> {match.group(3)}"

    return "\n".join(fix_line(line) for line in text.splitlines())


def _sanitize_cue_text(text: str) -> str:
    """Remove leaked timestamp lines from cue bodies."""
    lines: list[str] = []
    for line in text.splitlines():
        if _ARROW_LINE.match(line):
            continue
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def _parse_vtt_cues(text: str) -> list[ParsedCue]:
    body = text
    if body.startswith("WEBVTT"):
        body = body.split("\n", 1)[1] if "\n" in body else ""

    pattern = re.compile(
        rf"({_TIMESTAMP_PATTERN})\s*-->\s*({_TIMESTAMP_PATTERN})\s*\n"
        rf"(.*?)(?=\n(?:{_TIMESTAMP_PATTERN}|\d{{4}}:\d{{2}}[.,]\d{{3}})\s*-->|\Z)",
        re.DOTALL,
    )
    cues: list[ParsedCue] = []
    for start_ts, end_ts, body_text in pattern.findall(body):
        text_body = _sanitize_cue_text(body_text)
        if not text_body:
            continue
        cues.append(
            ParsedCue(
                start=_timestamp_to_seconds(start_ts),
                end=_timestamp_to_seconds(end_ts),
                text=text_body,
            )
        )
    return cues


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


def _collapse_spurious_cues(cues: list[ParsedCue]) -> list[ParsedCue]:
    """Drop Gemini micro-duplicate cues that share text and near-zero duration."""
    collapsed: list[ParsedCue] = []
    for cue in cues:
        duration = max(0.0, cue.end - cue.start)
        if collapsed:
            prev = collapsed[-1]
            same_text = cue.text == prev.text
            near_start = abs(cue.start - prev.start) < 0.25
            if 0 < duration < 0.05:
                if same_text:
                    collapsed[-1] = ParsedCue(prev.start, max(prev.end, cue.end), prev.text)
                continue
            if same_text and (duration < 0.25 or near_start):
                collapsed[-1] = ParsedCue(prev.start, max(prev.end, cue.end), prev.text)
                continue
        collapsed.append(cue)
    return collapsed


def _prepare_translated_cues(translated_text: str, fmt: str) -> list[ParsedCue]:
    cleaned = _normalize_malformed_vtt_timestamps(_strip_markdown_fence(translated_text))
    cues = _parse_srt_cues(cleaned) if fmt == "srt" else _parse_vtt_cues(cleaned)
    return _collapse_spurious_cues(cues)


def _text_length(text: str) -> int:
    return len(text.replace("\n", "").strip())


def _segment_duration(seg: SubtitleSegment) -> float:
    return max(0.0, seg.end - seg.start)


def _cue_matches_segment(
    seg: SubtitleSegment,
    cue: ParsedCue,
    *,
    tolerance: float,
) -> bool:
    if abs(cue.start - seg.start) > tolerance:
        return False

    source_len = _text_length(seg.text_zh)
    cue_len = _text_length(cue.text)
    if source_len <= 8 and cue_len > max(source_len * 5, 20):
        return False
    if _segment_duration(seg) < 0.12 and cue_len > 25:
        return False
    return True


def _split_multiline_to_followers(segments: list[SubtitleSegment]) -> None:
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


def _align_translated_segments(
    segments: list[SubtitleSegment],
    cues: list[ParsedCue],
    *,
    tolerance: float = 0.35,
) -> int:
    """Match cues to segments in timestamp order without stealing long cues for short segments."""
    used_cue_indices: set[int] = set()
    cue_index = 0

    for seg in segments:
        if seg.text_ja:
            continue

        while cue_index < len(cues) and cues[cue_index].start < seg.start - tolerance:
            cue_index += 1

        if cue_index >= len(cues):
            break

        cue = cues[cue_index]
        if abs(cue.start - seg.start) > tolerance:
            continue

        if _cue_matches_segment(seg, cue, tolerance=tolerance):
            seg.text_ja = cue.text
            used_cue_indices.add(cue_index)
            cue_index += 1

    _split_multiline_to_followers(segments)

    for seg in segments:
        if seg.text_ja:
            continue
        best_index: int | None = None
        best_diff = float("inf")
        for index, cue in enumerate(cues):
            if index in used_cue_indices:
                continue
            if not _cue_matches_segment(seg, cue, tolerance=tolerance):
                continue
            diff = abs(cue.start - seg.start)
            if diff < best_diff:
                best_diff = diff
                best_index = index
        if best_index is not None:
            seg.text_ja = cues[best_index].text
            used_cue_indices.add(best_index)

    _split_multiline_to_followers(segments)

    remaining_segments = [seg for seg in segments if not seg.text_ja]
    remaining_indices = [
        index for index in range(len(cues)) if index not in used_cue_indices
    ]
    if remaining_segments and remaining_indices:
        for cue_index in remaining_indices:
            lines = _split_cue_lines(cues[cue_index].text)
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
        if seg.text_ja:
            continue
        if _text_length(seg.text_zh) <= 8:
            seg.text_ja = ""
        else:
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
    cues = _prepare_translated_cues(translated_text, fmt)

    if len(cues) != len(segments):
        _log_segment_count_mismatch(
            source_count=len(segments),
            translated_count=len(cues),
            raw_response=translated_text,
            fmt=fmt,
        )

        logger.warning(
            "Segment count mismatch (source=%d, translated=%d). "
            "Attempting timestamp-based realignment.",
            len(segments),
            len(cues),
        )
        print(
            f"[WARN] セグメント数不一致のためタイムスタンプ照合で復旧を試みます "
            f"(原文 {len(segments)} / 翻訳 {len(cues)})",
            flush=True,
        )

    _align_translated_segments(segments, cues)

    for seg in segments:
        if seg.text_ja:
            seg.text_ja = _sanitize_cue_text(seg.text_ja)

    fallback_count = sum(
        1
        for seg in segments
        if seg.text_ja == seg.text_zh and _text_length(seg.text_zh) > 8
    )
    if fallback_count:
        logger.warning(
            "Used source text as fallback for %d segment(s) after realignment.",
            fallback_count,
        )
        print(
            f"[WARN] 復旧後も {fallback_count} セグメントは原文テキストで補完しました。",
            flush=True,
        )


def apply_translation_response(
    segments: list[SubtitleSegment],
    raw_response: str,
    *,
    fmt: str,
) -> None:
    """Apply batch translation response (JSON first, VTT alignment as fallback)."""
    json_matched = apply_translated_json(segments, raw_response)

    if json_matched == len(segments):
        logger.info("Batch JSON translation applied to all %d segments.", len(segments))
        return

    if json_matched > 0:
        logger.warning(
            "Batch JSON translation partial (%d/%d). "
            "Running VTT/timestamp fallback for remaining segments.",
            json_matched,
            len(segments),
        )
        print(
            f"[WARN] JSON翻訳が部分一致 ({json_matched}/{len(segments)})。"
            "VTT形式フォールバックで残りを復旧します。",
            flush=True,
        )
    else:
        logger.warning(
            "Batch JSON translation failed to parse; falling back to VTT alignment."
        )
        print(
            "[WARN] JSON翻訳のパースに失敗しました。VTT形式フォールバックを試みます。",
            flush=True,
        )

    apply_translated_subtitle_text(segments, raw_response, fmt)


def translate_segments(
    segments: list[SubtitleSegment],
    *,
    api_key: str,
    model_name: str,
    subtitle_fmt: str = "vtt",
) -> list[SubtitleSegment]:
    """Translate all segments in a single Gemini API request (no per-segment loop)."""
    from google import genai
    from google.genai import types

    if not segments:
        return segments

    client = genai.Client(api_key=api_key)
    payload = segments_to_translation_json(segments)
    segment_count = len(segments)

    logger.info(
        "Gemini batch translation: 1 API request for %d segments (model=%s)",
        segment_count,
        model_name,
    )
    print(
        f"[INFO] Gemini 一括翻訳: {segment_count} セグメントを 1 リクエストで送信します",
        flush=True,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=TRANSLATION_USER_PROMPT.format(payload=payload),
        config=types.GenerateContentConfig(
            system_instruction=TRANSLATION_SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    apply_translation_response(segments, response.text or "", fmt=subtitle_fmt)
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
