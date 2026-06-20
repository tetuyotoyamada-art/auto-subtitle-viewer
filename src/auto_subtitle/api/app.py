"""FastAPI application entry point."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from auto_subtitle.api.routes import router

load_dotenv()


def get_project_root() -> Path:
    """Resolve project root from this file: src/auto_subtitle/api/app.py -> root."""
    return Path(__file__).resolve().parents[3]


def get_frontend_dist() -> Path:
    return get_project_root() / "frontend" / "dist"


FRONTEND_DIST = get_frontend_dist()
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

app = FastAPI(
    title="Auto Subtitle Viewer API",
    description="中国語動画の音声認識・日本語翻訳・字幕生成 API",
    version="0.2.0",
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

assets_dir = FRONTEND_DIST / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


def _frontend_not_built_detail() -> str:
    return (
        "Frontend is not built. Run `build_frontend.bat` or "
        "`cd frontend && npm run build` first."
    )


@app.get("/")
async def serve_root() -> FileResponse:
    if not FRONTEND_INDEX.is_file():
        raise HTTPException(status_code=503, detail=_frontend_not_built_detail())
    return FileResponse(FRONTEND_INDEX)


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str) -> FileResponse:
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not Found")

    if not FRONTEND_DIST.is_dir():
        raise HTTPException(status_code=503, detail=_frontend_not_built_detail())

    requested = (FRONTEND_DIST / full_path).resolve()
    dist_root = FRONTEND_DIST.resolve()

    if not str(requested).startswith(str(dist_root)):
        raise HTTPException(status_code=404, detail="Not Found")

    if requested.is_file():
        return FileResponse(requested)

    if FRONTEND_INDEX.is_file():
        return FileResponse(FRONTEND_INDEX)

    raise HTTPException(status_code=503, detail=_frontend_not_built_detail())
