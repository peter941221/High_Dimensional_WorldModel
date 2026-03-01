@echo off
setlocal

REM One-click foreground launcher for the native research loop.
set "TEMPLATE_DIR=%~dp0"
if "%TEMPLATE_DIR:~-1%"=="\" set "TEMPLATE_DIR=%TEMPLATE_DIR:~0,-1%"
set "REPO_ROOT=%TEMPLATE_DIR%\.."
set "HAS_MAX_ITER=0"

for %%A in (%*) do (
  if /I "%%~A"=="-MaxIterations" set "HAS_MAX_ITER=1"
)

set "DEFAULT_MAX_ITER_ARGS="
if "%HAS_MAX_ITER%"=="0" (
  REM Explicit default: unlimited iterations unless user overrides.
  set "DEFAULT_MAX_ITER_ARGS=-MaxIterations 0"
)

echo [start_research] Template Dir: %TEMPLATE_DIR%
echo [start_research] Repo Root   : %REPO_ROOT%
echo [start_research] Starting foreground loop...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMPLATE_DIR%\scripts\Research_native_loop.ps1" ^
  -TemplatePath "%TEMPLATE_DIR%\RESEARCH_NATIVE_LOOP_TEMPLATE.json" ^
  -RepoRoot "%REPO_ROOT%" ^
  -PrdPath "%TEMPLATE_DIR%\RESEARCH_GOALS.md" ^
  -DevDocPath "%TEMPLATE_DIR%\RESEARCH_PLAN.md" ^
  -FindingsPath "%TEMPLATE_DIR%\FINDINGS.md" ^
  %DEFAULT_MAX_ITER_ARGS% ^
  %*

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [start_research] Exit code: %EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [start_research] Loop ended with error. Press any key to close.
  pause >nul
)
exit /b %EXIT_CODE%
