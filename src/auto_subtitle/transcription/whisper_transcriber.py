"""Speech-to-text transcription using faster-whisper."""

from __future__ import annotations

import logging
from pathlib import Path

from auto_subtitle.config import WhisperConfig
from auto_subtitle.subtitle.models import SubtitleSegment

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Extract timestamped Chinese text from video/audio via faster-whisper."""

    def __init__(self, config: WhisperConfig) -> None:
        self._config = config
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        from faster_whisper import WhisperModel

        logger.info(
            "Loading Whisper model: %s (device=%s, compute_type=%s)",
            self._config.model,
            self._config.device,
            self._config.compute_type,
        )
        self._model = WhisperModel(
            self._config.model,
            device=self._config.device,
            compute_type=self._config.compute_type,
        )
        return self._model

    def transcribe(self, media_path: Path) -> list[SubtitleSegment]:
        """Transcribe a media file and return timestamped segments."""
        if not media_path.exists():
            raise FileNotFoundError(f"Media file not found: {media_path}")

        model = self._load_model()
        logger.info("Transcribing: %s", media_path)

        segments_iter, _info = model.transcribe(
            str(media_path),
            language=self._config.language,
            vad_filter=True,
        )

        segments: list[SubtitleSegment] = []
        for index, seg in enumerate(segments_iter, start=1):
            segments.append(
                SubtitleSegment(
                    index=index,
                    start=seg.start,
                    end=seg.end,
                    text_zh=seg.text.strip(),
                )
            )

        logger.info("Transcription complete: %d segments", len(segments))
        return segments
