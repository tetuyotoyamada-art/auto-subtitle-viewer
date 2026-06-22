"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from auto_subtitle.core import DEFAULT_GEMINI_MODEL


@dataclass(frozen=True)
class WhisperConfig:
    model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str | None = None  # None = Whisper auto-detect


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model: str = DEFAULT_GEMINI_MODEL


@dataclass(frozen=True)
class AppConfig:
    whisper: WhisperConfig
    gemini: GeminiConfig
    output_format: str = "vtt"


def resolve_whisper_device(requested: str) -> str:
    """Use CUDA when requested and available; otherwise fall back to CPU."""
    if requested != "cuda":
        return requested
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def load_config(env_path: Path | None = None) -> AppConfig:
    """Load configuration from .env and environment variables."""
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill in your API key."
        )

    return AppConfig(
        whisper=WhisperConfig(
            model=os.getenv("WHISPER_MODEL", "large-v3"),
            device=os.getenv("WHISPER_DEVICE", "cuda"),
            compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "float16"),
        ),
        gemini=GeminiConfig(
            api_key=api_key,
            model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        ),
        output_format=os.getenv("SUBTITLE_FORMAT", "vtt"),
    )
