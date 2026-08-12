@echo off
setlocal
set "WEBTORA_FORCE_REPAIR=1"
call "%~dp0START_WEBTORA.bat"
exit /b %ERRORLEVEL%
