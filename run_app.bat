@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo  Auto Subtitle Viewer
echo ========================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Create it with: python -m venv .venv
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [WARN] Frontend build not found. Running build_frontend.bat ...
    call "%~dp0build_frontend.bat"
    if errorlevel 1 exit /b 1
    echo.
)

call ".venv\Scripts\activate.bat"

echo Opening browser: http://127.0.0.1:8000
start "" "http://127.0.0.1:8000"

echo Starting server on http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

uvicorn auto_subtitle.api.app:app --host 127.0.0.1 --port 8000
