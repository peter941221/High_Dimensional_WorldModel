@echo off
setlocal

set "TEMPLATE_DIR=%~dp0"
if "%TEMPLATE_DIR:~-1%"=="\" set "TEMPLATE_DIR=%TEMPLATE_DIR:~0,-1%"
set "MONITOR_PS1=%TEMPLATE_DIR%\scripts\Monitor_research_stream.ps1"

if /I "%~1"=="-h" goto :help
if /I "%~1"=="--help" goto :help
if /I "%~1"=="/?" goto :help

if not exist "%MONITOR_PS1%" (
  echo [monitor_research] Missing script: %MONITOR_PS1%
  exit /b 1
)

echo [monitor_research] Template Dir: %TEMPLATE_DIR%
echo [monitor_research] Starting monitor...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%MONITOR_PS1%" %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [monitor_research] Exit code: %EXIT_CODE%
exit /b %EXIT_CODE%

:help
echo Usage:
echo   monitor_research.bat
echo   monitor_research.bat -RunDir "C:\path\to\run_dir"
echo   monitor_research.bat -PollMs 800
echo   monitor_research.bat -DurationSec 60
exit /b 0
