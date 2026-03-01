@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM One-click foreground launcher for the native research loop.
set "TEMPLATE_DIR=%~dp0"
if "%TEMPLATE_DIR:~-1%"=="\" set "TEMPLATE_DIR=%TEMPLATE_DIR:~0,-1%"
set "REPO_ROOT=%TEMPLATE_DIR%\.."
set "HAS_MAX_ITER=0"
set "HAS_APPROVAL_MODE=0"

for %%A in (%*) do (
  if /I "%%~A"=="-MaxIterations" set "HAS_MAX_ITER=1"
  if /I "%%~A"=="-ContinueAfterApproval" set "HAS_APPROVAL_MODE=1"
  if /I "%%~A"=="-StopOnApproval" set "HAS_APPROVAL_MODE=1"
)

set "DEFAULT_MAX_ITER_ARGS="
if "%HAS_MAX_ITER%"=="0" (
  REM Explicit default: unlimited iterations unless user overrides.
  set "DEFAULT_MAX_ITER_ARGS=-MaxIterations 0"
)
set "DEFAULT_APPROVAL_MODE_ARGS="
if "%HAS_APPROVAL_MODE%"=="0" (
  REM Default behavior for starter: keep running even after approval until user stops it.
  set "DEFAULT_APPROVAL_MODE_ARGS=-ContinueAfterApproval"
)

REM Preflight lock check:
REM - If active loop is running, attach monitor instead of failing immediately.
REM - If lock is stale/corrupt, clear it and continue.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$lock = '%TEMPLATE_DIR%\runtime\active.lock';" ^
  "if (-not (Test-Path $lock)) { exit 0 }" ^
  "try { $j = Get-Content -Raw $lock | ConvertFrom-Json } catch { Remove-Item -Path $lock -Force -ErrorAction SilentlyContinue; Write-Host '[start_research] Cleared unreadable stale active.lock.'; exit 0 }" ^
  "$lockPid = if ($j.PSObject.Properties.Name -contains 'pid') { [int]$j.pid } else { -1 };" ^
  "$run = if ($j.PSObject.Properties.Name -contains 'run_id') { [string]$j.run_id } else { 'unknown' };" ^
  "$p = if ($lockPid -gt 0) { Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $lockPid) -ErrorAction SilentlyContinue } else { $null };" ^
  "if ($null -ne $p -and [string]$p.CommandLine -match 'Research_native_loop\.ps1') {" ^
  "  Write-Host ('[start_research] Active loop detected (run_id={0}, pid={1}). Opening monitor...' -f $run, $lockPid);" ^
  "  exit 23" ^
  "} else {" ^
  "  Remove-Item -Path $lock -Force -ErrorAction SilentlyContinue;" ^
  "  Write-Host '[start_research] Cleared stale active.lock before start.';" ^
  "  exit 0" ^
  "}"
set "LOCK_CHECK_EXIT=%ERRORLEVEL%"
if "%LOCK_CHECK_EXIT%"=="23" (
  call "%TEMPLATE_DIR%\monitor_research.bat"
  exit /b 0
)

echo [start_research] Template Dir: %TEMPLATE_DIR%
echo [start_research] Repo Root   : %REPO_ROOT%
if "%HAS_MAX_ITER%"=="1" (
  echo [start_research] MaxIterations explicitly set by user args.
) else (
  echo [start_research] MaxIterations default = unlimited ^(-MaxIterations 0^).
)
if "%HAS_APPROVAL_MODE%"=="1" (
  echo [start_research] Approval stop mode explicitly set by user args.
) else (
  echo [start_research] Approval mode default = continue after approval.
)
echo [start_research] Starting foreground loop...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMPLATE_DIR%\scripts\Research_native_loop.ps1" ^
  -TemplatePath "%TEMPLATE_DIR%\RESEARCH_NATIVE_LOOP_TEMPLATE.json" ^
  -RepoRoot "%REPO_ROOT%" ^
  -PrdPath "%TEMPLATE_DIR%\RESEARCH_GOALS.md" ^
  -DevDocPath "%TEMPLATE_DIR%\RESEARCH_PLAN.md" ^
  -FindingsPath "%TEMPLATE_DIR%\FINDINGS.md" ^
  %DEFAULT_MAX_ITER_ARGS% ^
  %DEFAULT_APPROVAL_MODE_ARGS% ^
  %*

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [start_research] Exit code: %EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo [start_research] Loop ended with error. Press any key to close.
  pause >nul
)
exit /b %EXIT_CODE%
