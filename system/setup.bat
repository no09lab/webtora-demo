@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title WebTora-beta Setup
chcp 65001 >nul 2>&1

if not defined WEBTORA_SUBST_ACTIVE (
    echo [ERROR] Please run START_WEBTORA.bat instead of setup.bat directly.
    echo The launcher creates the ASCII-only path required by MediaPipe.
    echo.
    pause
    exit /b 12
)

echo ========================================
echo  WebTora-beta - Runtime Setup v8
echo ========================================
echo Runtime path: %CD%
echo.

del /q "webtora_setup_error.log" >nul 2>&1
set "SETUP_STAGE=Python detection"
set "PYTHON_CMD="

rem Prefer the Windows Python Launcher with Python 3.10.
py -3.10 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3.10"

rem Fallback to python on PATH, but only when it is Python 3.10.
if not defined PYTHON_CMD (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10 was not found.
    echo Install Python 3.10 64-bit, then run START_WEBTORA.bat again.
    echo Creating a GPT support diagnostic file...
    call "%~dp0GPT_SUPPORT.bat" /silent >nul 2>&1
    echo Open the support folder and upload AI\GPT_SUPPORT_SETUP.txt with WEBTORA_GPT_DIAGNOSTICS.txt to your GPT.
    echo.
    pause
    exit /b 10
)

echo [1/7] Python 3.10 found.
set "SETUP_STAGE=Virtual environment creation"

if not exist ".venv\Scripts\python.exe" (
    echo [2/7] Creating WebTora-beta virtual environment...
    %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 goto :setup_failed
) else (
    echo [2/7] Existing virtual environment found.
)

set "SETUP_STAGE=Updating pip/setuptools/wheel"
echo [3/7] Updating installer tools...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
if errorlevel 1 goto :setup_failed

set "SETUP_STAGE=Removing conflicting MediaPipe/OpenCV packages"
echo [4/7] Removing old MediaPipe/OpenCV packages...
".venv\Scripts\python.exe" -m pip uninstall -y mediapipe opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1

set "SETUP_STAGE=Installing requirements.txt"
echo [5/7] Installing a clean WebTora-beta environment...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --no-cache-dir -r "requirements.txt"
if errorlevel 1 goto :setup_failed

set "SETUP_STAGE=Checking MediaPipe resource files"
echo [6/7] Checking MediaPipe resource files...
".venv\Scripts\python.exe" -c "import os,sys,mediapipe as mp; p=os.path.join(os.path.dirname(mp.__file__),'modules','pose_landmark','pose_landmark_cpu.binarypb'); print('[WebTora-beta] Python:',sys.version.split()[0]); print('[WebTora-beta] MediaPipe:',mp.__version__); print('[WebTora-beta] MediaPipe path:',mp.__file__); print('[WebTora-beta] pose graph:',p); print('[WebTora-beta] pose graph exists:',os.path.exists(p)); raise SystemExit(0 if os.path.exists(p) else 31)"
if errorlevel 1 goto :setup_failed

set "SETUP_STAGE=Testing MediaPipe Pose initialization"
echo [7/7] Testing MediaPipe Pose initialization...
".venv\Scripts\python.exe" -c "import mediapipe as mp; p=mp.solutions.pose.Pose(model_complexity=0); p.close(); print('[WebTora-beta] MediaPipe Pose initialization OK')"
if errorlevel 1 goto :setup_failed

> ".webtora_setup_v8_complete" echo setup complete

echo.
echo ========================================
echo  Setup complete.
echo  MediaPipe Pose test: OK
echo ========================================
echo.
if not defined WEBTORA_AUTO_SETUP pause
exit /b 0

:setup_failed
set "SETUP_ERROR=%ERRORLEVEL%"
> "webtora_setup_error.log" echo WebTora-beta setup failed
>> "webtora_setup_error.log" echo Date: %DATE% %TIME%
>> "webtora_setup_error.log" echo Stage: %SETUP_STAGE%
>> "webtora_setup_error.log" echo Error level: %SETUP_ERROR%
>> "webtora_setup_error.log" echo Runtime path: %CD%
>> "webtora_setup_error.log" echo Python command: %PYTHON_CMD%
echo.
echo ========================================
echo  Setup failed.
echo ========================================
echo WebTora-beta could not create a working MediaPipe environment.
echo Creating a GPT support diagnostic file...
call "%~dp0GPT_SUPPORT.bat" /silent >nul 2>&1
echo Open the support folder and upload AI\GPT_SUPPORT_SETUP.txt with WEBTORA_GPT_DIAGNOSTICS.txt to your GPT.
echo.
pause
exit /b 1
