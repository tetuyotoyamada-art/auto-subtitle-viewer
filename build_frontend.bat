@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================
echo  Auto Subtitle Viewer - Frontend Build
echo ========================================
echo.

if not exist "frontend\package.json" (
    echo [ERROR] frontend\package.json not found.
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH.
    echo Install Node.js from https://nodejs.org/
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        exit /b 1
    )
    popd
    echo.
)

echo Building frontend...
pushd frontend
call npm run build
set BUILD_EXIT=!ERRORLEVEL!
popd

if !BUILD_EXIT! neq 0 (
    echo.
    echo [ERROR] Frontend build failed.
    exit /b 1
)

echo.
echo [OK] Build complete: frontend\dist\
echo You can now run run_app.bat to start the app.
exit /b 0
