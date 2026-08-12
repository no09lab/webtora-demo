@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title WebTora-beta GPT Support
if not defined WEBTORA_PACKAGE_ROOT set "WEBTORA_PACKAGE_ROOT=%~dp0..\"
if not defined WEBTORA_SUPPORT_DIR set "WEBTORA_SUPPORT_DIR=%WEBTORA_PACKAGE_ROOT%support\"
if not defined WEBTORA_AI_DIR set "WEBTORA_AI_DIR=%WEBTORA_SUPPORT_DIR%AI\"

if defined WEBTORA_SUBST_ACTIVE goto :mapped
set "WEBTORA_SUBST_DRIVE="
for %%D in (W V U T S R Q P O N M L K J I H G F Z Y X) do (
  subst %%D: "%CD%" >nul 2>&1
  if not errorlevel 1 (
    set "WEBTORA_SUBST_DRIVE=%%D:"
    goto :subst_ready
  )
)
goto :mapped

:subst_ready
set "WEBTORA_SUBST_ACTIVE=1"
call "%WEBTORA_SUBST_DRIVE%\GPT_SUPPORT.bat" %*
set "RC=%ERRORLEVEL%"
subst %WEBTORA_SUBST_DRIVE% /d >nul 2>&1
exit /b %RC%

:mapped
cd /d "%~dp0"
if not exist "%WEBTORA_SUPPORT_DIR%" mkdir "%WEBTORA_SUPPORT_DIR%" >nul 2>&1
set "OUT=%WEBTORA_SUPPORT_DIR%WEBTORA_GPT_DIAGNOSTICS.txt"

> "%OUT%" echo WebTora-beta GPT diagnostics - basic launcher report
>> "%OUT%" echo Generated: %DATE% %TIME%
>> "%OUT%" echo Current directory: %CD%
>> "%OUT%" echo Package root: %WEBTORA_PACKAGE_ROOT%
>> "%OUT%" echo Support dir: %WEBTORA_SUPPORT_DIR%
>> "%OUT%" echo AI dir: %WEBTORA_AI_DIR%
>> "%OUT%" echo.
>> "%OUT%" echo [Python discovery]
where py >> "%OUT%" 2>&1
py -0p >> "%OUT%" 2>&1
where python >> "%OUT%" 2>&1
python --version >> "%OUT%" 2>&1
>> "%OUT%" echo.
>> "%OUT%" echo [.venv]
if exist ".venv\Scripts\python.exe" (>> "%OUT%" echo .venv Python exists: YES) else (>> "%OUT%" echo .venv Python exists: NO)

set "REPORT_PY="
if exist ".venv\Scripts\python.exe" set "REPORT_PY=.venv\Scripts\python.exe"
if not defined REPORT_PY (
    py -3.10 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "REPORT_PY=py -3.10"
)
if not defined REPORT_PY (
    python -c "import sys" >nul 2>&1
    if not errorlevel 1 set "REPORT_PY=python"
)
if defined REPORT_PY (
    %REPORT_PY% "webutoracore\webutora_support_report.py" "%OUT%"
) else (
    >> "%OUT%" echo.
    >> "%OUT%" echo [ERROR]
    >> "%OUT%" echo No usable Python runtime was found. Install Python 3.10 64-bit.
)

echo.
echo ========================================
echo  WebTora-beta GPT support file created
echo ========================================
echo %OUT%
echo.
echo Upload BOTH files to your GPT:
echo   1. %WEBTORA_AI_DIR%GPT_SUPPORT_SETUP.txt
echo   2. %OUT%
echo.
if /I not "%~1"=="/silent" (
    explorer /select,"%OUT%" >nul 2>&1
    pause
)
exit /b 0
