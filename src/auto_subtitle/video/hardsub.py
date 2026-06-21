"""Burn translated subtitles into video via FFmpeg."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from auto_subtitle.subtitle.models import SubtitleSegment

logger = logging.getLogger(__name__)

DEFAULT_FONT_NAME = "Yu Gothic UI"
PREVIEW_REFERENCE_HEIGHT = 480
PREVIEW_BOTTOM_MARGIN_RATIO = 0.12
PREVIEW_HORIZONTAL_MARGIN_RATIO = 0.05

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".wmv", ".flv"}


@dataclass(frozen=True)
class HardsubStyle:
    font_name: str = DEFAULT_FONT_NAME
    font_size: int = 22
    font_color: str = "#ffffff"
    background_color: str = "rgba(0, 0, 0, 0.55)"


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "ffmpeg が見つかりません。https://ffmpeg.org からインストールし、PATH に追加してください。"
        )
    return path


def _find_ffprobe() -> str:
    ffmpeg = find_ffmpeg()
    sibling = Path(ffmpeg).with_name("ffprobe.exe" if ffmpeg.lower().endswith(".exe") else "ffprobe")
    if sibling.is_file():
        return str(sibling)
    path = shutil.which("ffprobe")
    if not path:
        raise FileNotFoundError("ffprobe が見つかりません。FFmpeg と一緒にインストールしてください。")
    return path


def _probe_video_size(video_path: Path) -> tuple[int, int]:
    command = [
        _find_ffprobe(),
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise RuntimeError("動画の解像度を取得できませんでした。")
    width = int(streams[0]["width"])
    height = int(streams[0]["height"])
    return width, height


def _escape_subtitles_filter_path(path: Path) -> str:
    normalized = path.resolve().as_posix()
    normalized = normalized.replace("'", r"\'")
    normalized = normalized.replace(":", r"\:")
    return normalized


def _parse_css_color(color: str) -> tuple[int, int, int, float]:
    stripped = color.strip()
    rgba_match = re.match(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)",
        stripped,
        re.IGNORECASE,
    )
    if rgba_match:
        red = int(rgba_match.group(1))
        green = int(rgba_match.group(2))
        blue = int(rgba_match.group(3))
        opacity = float(rgba_match.group(4) if rgba_match.group(4) is not None else 1.0)
        return red, green, blue, max(0.0, min(1.0, opacity))

    hex_match = re.fullmatch(r"#?([0-9a-fA-F]{6})", stripped)
    if hex_match:
        rgb = hex_match.group(1)
        return int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16), 1.0

    return 255, 255, 255, 1.0


def _to_ass_color(color: str) -> str:
    """Convert CSS color to ASS &HAABBGGRR (AA=00 opaque, FF transparent)."""
    red, green, blue, opacity = _parse_css_color(color)
    transparency = int(round((1.0 - opacity) * 255))
    return f"&H{transparency:02X}{blue:02X}{green:02X}{red:02X}"


def _scale_for_video(value_px: int, video_height: int) -> int:
    return max(1, round(value_px * video_height / PREVIEW_REFERENCE_HEIGHT))


def _format_ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int(round((seconds % 1) * 100)) % 100
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def write_ass_file(
    segments: list[SubtitleSegment],
    ass_path: Path,
    *,
    style: HardsubStyle,
    video_width: int,
    video_height: int,
) -> Path:
    """Write ASS subtitles styled to match the browser preview overlay."""
    ass_font_size = _scale_for_video(style.font_size, video_height)
    margin_v = round(video_height * PREVIEW_BOTTOM_MARGIN_RATIO)
    margin_lr = round(video_width * PREVIEW_HORIZONTAL_MARGIN_RATIO)
    box_padding = max(2, round(ass_font_size * 0.18))
    shadow = max(1, round(ass_font_size * 0.05))

    primary = _to_ass_color(style.font_color)
    back = _to_ass_color(style.background_color)
    shadow_color = _to_ass_color("rgba(0, 0, 0, 0.8)")

    header = f"""[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Preview,{style.font_name},{ass_font_size},{primary},&H000000FF,{shadow_color},{back},0,0,0,0,100,100,0,0,4,{box_padding},{shadow},2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [header.rstrip(), ""]
    for seg in segments:
        text = _ass_escape((seg.text_ja or seg.text_zh).strip())
        if not text:
            continue
        start = _format_ass_time(seg.start)
        end = _format_ass_time(seg.end)
        lines.append(
            f"Dialogue: 0,{start},{end},Preview,,0,0,0,,{text}"
        )

    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return ass_path


def burn_subtitles_into_video(
    video_path: Path,
    segments: list[SubtitleSegment],
    output_path: Path,
    *,
    font_name: str = DEFAULT_FONT_NAME,
    font_size: int = 22,
    font_color: str = "#ffffff",
    background_color: str = "rgba(0, 0, 0, 0.55)",
) -> Path:
    """Hard-sub translated segments into a new MP4 file."""
    if not segments:
        raise ValueError("字幕セグメントがありません。")

    if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(
            f"動画ファイル形式 ({video_path.suffix}) には字幕焼き付けに対応していません。"
        )

    ffmpeg = find_ffmpeg()
    video_width, video_height = _probe_video_size(video_path)
    style = HardsubStyle(
        font_name=font_name,
        font_size=font_size,
        font_color=font_color,
        background_color=background_color,
    )

    ass_path = video_path.parent / "hardsub.ass"
    write_ass_file(
        segments,
        ass_path,
        style=style,
        video_width=video_width,
        video_height=video_height,
    )

    escaped_ass = _escape_subtitles_filter_path(ass_path)
    vf = f"subtitles='{escaped_ass}'"

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    logger.info(
        "Running FFmpeg hardsub: %s -> %s (%dx%d, font=%spx->%spx)",
        video_path.name,
        output_path.name,
        video_width,
        video_height,
        style.font_size,
        _scale_for_video(style.font_size, video_height),
    )
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        logger.error("FFmpeg hardsub failed: %s", stderr)
        raise RuntimeError(f"FFmpeg による字幕焼き付けに失敗しました: {stderr or exc}") from exc

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("字幕付き動画ファイルの生成に失敗しました。")

    return output_path
