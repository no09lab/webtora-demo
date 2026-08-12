@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
set "WEBTORA_PACKAGE_ROOT=%~dp0"
set "WEBTORA_SUPPORT_DIR=%~dp0support\"
set "WEBTORA_AI_DIR=%~dp0support\AI\"
cd /d "%~dp0system"
call START_WEBTORA.bat
exit /b %ERRORLEVEL%
