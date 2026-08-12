@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title WebTora-beta Camera Test
chcp 65001 >nul 2>&1
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
echo [ERROR] Could not create a temporary ASCII-only drive path.
pause
exit /b 20

:subst_ready
set "WEBTORA_SUBST_ACTIVE=1"
call "%WEBTORA_SUBST_DRIVE%\CAMERA_TEST.bat"
set "RC=%ERRORLEVEL%"
subst %WEBTORA_SUBST_DRIVE% /d >nul 2>&1
exit /b %RC%

:mapped
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto :setup
if not exist ".webtora_setup_v8_complete" goto :setup
goto :test

:setup
set "WEBTORA_AUTO_SETUP=1"
call "%~dp0setup.bat"
set "WEBTORA_AUTO_SETUP="
if errorlevel 1 exit /b 1

:test
echo [WebTora-beta] Close WebTora-beta and other camera apps before this test.
echo.
".venv\Scripts\python.exe" "webutoracore\camera_only_test.py"
echo.
pause
