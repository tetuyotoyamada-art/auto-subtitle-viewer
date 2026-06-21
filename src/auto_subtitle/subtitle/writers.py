"""WebVTT and SRT subtitle file writers."""

from __future__ import annotations

from pathlib import Path

from auto_subtitle.subtitle.models import SubtitleSegment


def _format_timestamp(seconds: float, *, separator: str = ".") -> str:
    """Convert seconds to HH:MM:SS.mmm (VTT) or HH:MM:SS,mmm (SRT)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def format_vtt_content(segments: list[SubtitleSegment]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp(seg.start, separator=".")
        end = _format_timestamp(seg.end, separator=".")
        lines.append(f"{start} --> {end}")
        lines.append(seg.text_ja or seg.text_zh)
        lines.append("")
    return "\n".join(lines)


def format_srt_content(segments: list[SubtitleSegment]) -> str:
    lines: list[str] = []
    for seg in segments:
        start = _format_timestamp(seg.start, separator=",")
        end = _format_timestamp(seg.end, separator=",")
        lines.append(str(seg.index))
        lines.append(f"{start} --> {end}")
        lines.append(seg.text_ja or seg.text_zh)
        lines.append("")
    return "\n".join(lines)


def segments_to_srt_text(segments: list[SubtitleSegment]) -> str:
    """Build standard SRT subtitle text from segment timing and translated text."""
    return format_srt_content(segments)


def format_subtitle_content(segments: list[SubtitleSegment], fmt: str) -> str:
    if fmt == "srt":
        return format_srt_content(segments)
    return format_vtt_content(segments)


def write_vtt(segments: list[SubtitleSegment], output_path: Path) -> Path:
    """Write subtitle segments to a WebVTT file."""
    output_path.write_text(format_vtt_content(segments), encoding="utf-8")
    return output_path


def write_srt(segments: list[SubtitleSegment], output_path: Path) -> Path:
    """Write subtitle segments to an SRT file."""
    output_path.write_text(format_srt_content(segments), encoding="utf-8")
    return output_path

