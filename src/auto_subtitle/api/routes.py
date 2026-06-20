"""API route handlers."""

from __future__ import annotations

import asyncio
import json
import queue
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from auto_subtitle.api.schemas import (
    HealthResponse,
    PathGenerateRequest,
    ProgressEvent,
    SegmentResponse,
    SubtitleGenerateResponse,
)
from auto_subtitle.config import AppConfig, load_config
from auto_subtitle.core import ProcessOptions, process_media

router = APIRouter()


def _to_response(result_format: str, segments, subtitle_content: str) -> SubtitleGenerateResponse:
    return SubtitleGenerateResponse(
        format=result_format,  # type: ignore[arg-type]
        subtitle_content=subtitle_content,
        segments=[
            SegmentResponse(
                index=seg.index,
                start=seg.start,
                end=seg.end,
                text_zh=seg.text_zh,
                text_ja=seg.text_ja,
            )
            for seg in segments
        ],
        segment_count=len(segments),
    )


def _build_options(
    config: AppConfig,
    *,
    format: str,
    whisper_model: str,
    device: str,
    compute_type: str,
    gemini_model: str | None,
) -> ProcessOptions:
    compute = compute_type
    if device == "cpu" and compute == "float16":
        compute = "int8"

    return ProcessOptions(
        whisper_model=whisper_model,
        device=device,  # type: ignore[arg-type]
        compute_type=compute,
        subtitle_fmt=format,  # type: ignore[arg-type]
        gemini_model=gemini_model or config.gemini.model,
    )


def _run_pipeline(
    media_path: Path,
    config: AppConfig,
    options: ProcessOptions,
    on_progress=None,
):
    return process_media(
        media_path,
        api_key=config.gemini.api_key,
        options=options,
        on_progress=on_progress,
    )


def _format_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _progress_payload(stage: str, message: str, segment_count: int | None) -> dict:
    event = ProgressEvent(stage=stage, message=message, segment_count=segment_count)  # type: ignore[arg-type]
    return event.model_dump()


async def _stream_pipeline_events(media_path: Path, config: AppConfig, options: ProcessOptions):
    event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()

    def on_progress(stage: str, message: str, segment_count: int | None = None) -> None:
        event_queue.put(
            (
                "progress",
                _progress_payload(stage, message, segment_count),
            )
        )

    def worker() -> None:
        try:
            result = _run_pipeline(media_path, config, options, on_progress=on_progress)
            response = _to_response(result.format, result.segments, result.subtitle_content)
            event_queue.put(("complete", response.model_dump()))
        except FileNotFoundError as exc:
            event_queue.put(("error", {"detail": str(exc), "status_code": 404}))
        except ValueError as exc:
            event_queue.put(("error", {"detail": str(exc), "status_code": 400}))
        except Exception as exc:
            event_queue.put(("error", {"detail": str(exc), "status_code": 500}))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while True:
        event_name, payload = await asyncio.to_thread(event_queue.get)
        yield _format_sse(event_name, payload)
        if event_name in {"complete", "error"}:
            break

    await asyncio.to_thread(thread.join)


async def _save_upload(file: UploadFile) -> tuple[Path, Path]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = Path(file.filename).suffix or ".mp4"
    temp_dir = Path(tempfile.mkdtemp(prefix="auto-subtitle-"))
    media_path = temp_dir / f"upload{suffix}"

    with media_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return temp_dir, media_path


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/subtitles/generate", response_model=SubtitleGenerateResponse)
async def generate_from_upload(
    file: UploadFile = File(..., description="Video or audio file"),
    format: Literal["vtt", "srt"] = Form("vtt"),
    whisper_model: str = Form("large-v3"),
    device: Literal["cuda", "cpu"] = Form("cuda"),
    compute_type: str = Form("float16"),
    gemini_model: str | None = Form(None),
) -> SubtitleGenerateResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = Path(file.filename).suffix or ".mp4"
    config = load_config()
    options = _build_options(
        config,
        format=format,
        whisper_model=whisper_model,
        device=device,
        compute_type=compute_type,
        gemini_model=gemini_model,
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="auto-subtitle-"))
    media_path = temp_dir / f"upload{suffix}"

    try:
        with media_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = await asyncio.to_thread(_run_pipeline, media_path, config, options)
        return _to_response(result.format, result.segments, result.subtitle_content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/subtitles/generate-stream")
async def generate_from_upload_stream(
    file: UploadFile = File(..., description="Video or audio file"),
    format: Literal["vtt", "srt"] = Form("vtt"),
    whisper_model: str = Form("large-v3"),
    device: Literal["cuda", "cpu"] = Form("cuda"),
    compute_type: str = Form("float16"),
    gemini_model: str | None = Form(None),
) -> StreamingResponse:
    config = load_config()
    options = _build_options(
        config,
        format=format,
        whisper_model=whisper_model,
        device=device,
        compute_type=compute_type,
        gemini_model=gemini_model,
    )

    temp_dir, media_path = await _save_upload(file)

    async def event_stream():
        try:
            async for chunk in _stream_pipeline_events(media_path, config, options):
                yield chunk
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/subtitles/generate-path", response_model=SubtitleGenerateResponse)
async def generate_from_path(body: PathGenerateRequest) -> SubtitleGenerateResponse:
    media_path = Path(body.file_path).expanduser().resolve()
    if not media_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {media_path}")

    config = load_config()
    options = _build_options(
        config,
        format=body.format,
        whisper_model=body.whisper_model,
        device=body.device,
        compute_type=body.compute_type,
        gemini_model=body.gemini_model,
    )

    try:
        result = await asyncio.to_thread(_run_pipeline, media_path, config, options)
        return _to_response(result.format, result.segments, result.subtitle_content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
