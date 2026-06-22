@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo  Auto Subtitle Viewer
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run setup.bat first for first-time setup.
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env not found.
    echo Run setup.bat or copy .env.example to .env and set GEMINI_API_KEY.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uvicorn is not installed in .venv.
    echo Run setup.bat or: pip install -r requirements.txt ^&^& pip install -e .
    exit /b 1
)

if not exist "frontend\dist\index.html" (
    echo [WARN] Frontend build not found. Running build_frontend.bat ...
    call "%~dp0build_frontend.bat"
    if errorlevel 1 exit /b 1
    echo.
)

echo Opening browser: http://127.0.0.1:8000
start "" "http://127.0.0.1:8000"

echo Starting server on http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

python -m uvicorn auto_subtitle.api.app:app --host 127.0.0.1 --port 8000
