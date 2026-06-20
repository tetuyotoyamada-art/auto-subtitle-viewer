"""End-to-end pipeline: transcribe -> translate -> subtitle output."""

from __future__ import annotations

import logging
from pathlib import Path

from auto_subtitle.config import AppConfig
from auto_subtitle.core import ProcessOptions, ProcessResult, process_media
from auto_subtitle.subtitle.writers import write_srt, write_vtt

logger = logging.getLogger(__name__)


class SubtitlePipeline:
    """Orchestrate the full subtitle generation workflow."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def _build_options(self, subtitle_fmt: str | None = None) -> ProcessOptions:
        whisper = self._config.whisper
        return ProcessOptions(
            whisper_model=whisper.model,
            device=whisper.device,
            compute_type=whisper.compute_type,
            subtitle_fmt=subtitle_fmt or self._config.output_format,
            gemini_model=self._config.gemini.model,
        )

    def run(
        self,
        media_path: Path,
        output_path: Path | None = None,
        *,
        subtitle_fmt: str | None = None,
    ) -> ProcessResult:
        """Process a media file and optionally write a subtitle file."""
        media_path = media_path.resolve()
        fmt = (subtitle_fmt or self._config.output_format).lower()

        logger.info("Starting pipeline for: %s", media_path)
        result = process_media(
            media_path,
            api_key=self._config.gemini.api_key,
            options=self._build_options(fmt),
        )

        if output_path is None:
            output_path = media_path.with_suffix(f".{fmt}")
        else:
            output_path = output_path.resolve()

        if fmt == "srt":
            write_srt(result.segments, output_path)
        else:
            write_vtt(result.segments, output_path)

        logger.info("Subtitle file written: %s", output_path)
        return result
