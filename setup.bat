@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================
echo  Auto Subtitle Viewer - First-time Setup
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VER=%%v
echo Using Python %PYTHON_VER%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
    echo.
) else (
    echo Virtual environment already exists.
    echo.
)

call ".venv\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo.
echo Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Installing package (editable)...
python -m pip install -e .
if errorlevel 1 exit /b 1

if not exist ".env" (
    echo.
    echo Creating .env from .env.example...
    copy /Y ".env.example" ".env" >nul
    echo [IMPORTANT] Edit .env and set GEMINI_API_KEY before running the app.
) else (
    echo.
    echo .env already exists. Skipping copy.
)

echo.
echo Optional: GPU acceleration (CUDA 12, NVIDIA driver required)
echo   python -m pip install -r requirements-cuda.txt
echo.

where npm >nul 2>&1
if errorlevel 1 (
    echo [WARN] npm not found. Install Node.js 18+ to build the frontend later.
) else (
    echo Building frontend...
    call "%~dp0build_frontend.bat"
    if errorlevel 1 exit /b 1
)

echo.
echo ========================================
echo  Setup complete
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env  (GEMINI_API_KEY and Whisper settings for this PC)
echo   2. Run run_app.bat
echo.
echo PowerShell users: use .venv\Scripts\Activate.ps1 (not activate.bat)
echo.
exit /b 0
