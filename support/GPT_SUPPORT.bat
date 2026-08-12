@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
set "WEBTORA_PACKAGE_ROOT=%~dp0..\"
set "WEBTORA_SUPPORT_DIR=%~dp0"
set "WEBTORA_AI_DIR=%~dp0AI\"
cd /d "%~dp0..\system"
call GPT_SUPPORT.bat %*
exit /b %ERRORLEVEL%
