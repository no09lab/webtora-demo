@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title WebTora-beta Launcher
chcp 65001 >nul 2>&1

if not defined WEBTORA_PACKAGE_ROOT set "WEBTORA_PACKAGE_ROOT=%~dp0..\"
if not defined WEBTORA_SUPPORT_DIR set "WEBTORA_SUPPORT_DIR=%WEBTORA_PACKAGE_ROOT%support\"
if not defined WEBTORA_AI_DIR set "WEBTORA_AI_DIR=%WEBTORA_SUPPORT_DIR%AI\"

rem MediaPipe legacy Solutions can fail on Windows when its resource path
rem contains non-ASCII characters. Always launch through a temporary
rem drive-letter alias so MediaPipe sees an ASCII-only path such as W:\.
if defined WEBTORA_SUBST_ACTIVE goto :mapped_launch

if not defined WEBTORA_ORIGINAL_DIR set "WEBTORA_ORIGINAL_DIR=%CD%"
set "WEBTORA_SUBST_DRIVE="
for %%D in (W V U T S R Q P O N M L K J I H G F Z Y X) do (
    subst %%D: "%CD%" >nul 2>&1
    if not errorlevel 1 (
        set "WEBTORA_SUBST_DRIVE=%%D:"
        goto :subst_ready
    )
)

echo [ERROR] WebTora-beta could not create a temporary drive alias.
echo MediaPipe needs an ASCII-only runtime path on this Windows environment.
echo Creating a GPT support diagnostic file...
call "%~dp0GPT_SUPPORT.bat" /silent >nul 2>&1
echo Open the support folder and upload AI\GPT_SUPPORT_SETUP.txt
echo together with WEBTORA_GPT_DIAGNOSTICS.txt to your GPT.
echo.
pause
exit /b 20

:subst_ready
set "WEBTORA_SUBST_ACTIVE=1"
echo [WebTora-beta] MediaPipe compatibility path: %WEBTORA_SUBST_DRIVE%\
call "%WEBTORA_SUBST_DRIVE%\START_WEBTORA.bat"
set "WEBTORA_EXIT=%ERRORLEVEL%"
subst %WEBTORA_SUBST_DRIVE% /d >nul 2>&1
exit /b %WEBTORA_EXIT%

:mapped_launch
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto :first_setup
if defined WEBTORA_FORCE_REPAIR goto :first_setup
if not exist ".webtora_setup_v8_complete" goto :first_setup
goto :launch

:first_setup
echo [WebTora-beta] Runtime setup/update is required.
echo [WebTora-beta] This also repairs the MediaPipe installation.
echo.
set "WEBTORA_AUTO_SETUP=1"
call "%~dp0setup.bat"
set "WEBTORA_AUTO_SETUP="
if errorlevel 1 exit /b 1

:launch
echo [WebTora-beta] Starting from ASCII compatibility path: %CD%
del /q "webtora_last_error.log" >nul 2>&1
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" "webutoracore\webutora_osc_sender.py"
set "WEBTORA_EXIT=%ERRORLEVEL%"
if "%WEBTORA_EXIT%"=="0" exit /b 0

echo.
echo ========================================
echo  WebTora-beta stopped with an error.
echo  Exit code: %WEBTORA_EXIT%
echo ========================================
echo Creating a GPT support diagnostic file...
call "%~dp0GPT_SUPPORT.bat" /silent >nul 2>&1
echo.
echo Open the support folder and upload:
echo   AI\GPT_SUPPORT_SETUP.txt
echo   WEBTORA_GPT_DIAGNOSTICS.txt
echo.
pause
exit /b %WEBTORA_EXIT%
