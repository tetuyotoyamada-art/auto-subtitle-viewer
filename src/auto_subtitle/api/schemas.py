"""Pydantic schemas for the REST API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SegmentResponse(BaseModel):
    index: int
    start: float
    end: float
    text_zh: str
    text_ja: str


class SubtitleGenerateResponse(BaseModel):
    format: Literal["vtt", "srt"]
    subtitle_content: str
    segments: list[SegmentResponse]
    segment_count: int


class PathGenerateRequest(BaseModel):
    file_path: str = Field(..., description="Local path to a video/audio file")
    format: Literal["vtt", "srt"] = "vtt"
    whisper_model: str | None = None
    device: Literal["cuda", "cpu"] | None = None
    compute_type: str | None = None
    gemini_model: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"


class AppConfigResponse(BaseModel):
    status: str = "ok"
    whisper_device: Literal["cuda", "cpu"]
    whisper_model: str
    whisper_compute_type: str


class ProgressEvent(BaseModel):
    stage: Literal[
        "preparing",
        "transcribing",
        "transcribed",
        "translating",
        "formatting",
        "complete",
    ]
    message: str
    segment_count: int | None = None
