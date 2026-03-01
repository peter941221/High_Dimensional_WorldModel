@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Stop the currently active research loop run (best-effort) by reading runtime\active.lock.
set "TEMPLATE_DIR=%~dp0"
if "%TEMPLATE_DIR:~-1%"=="\" set "TEMPLATE_DIR=%TEMPLATE_DIR:~0,-1%"
set "LOCK_FILE=%TEMPLATE_DIR%\runtime\active.lock"

if not exist "%LOCK_FILE%" (
  echo [stop_research] No active.lock found: %LOCK_FILE%
  exit /b 0
)

for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "try { (Get-Content -Raw '%LOCK_FILE%' | ConvertFrom-Json).pid } catch { '' }"`) do (
  set "LOCK_PID=%%L"
)

if "%LOCK_PID%"=="" (
  echo [stop_research] Could not parse pid from active.lock. Deleting lock only.
  cmd /c del /f /q "%LOCK_FILE%" >nul 2>nul
  exit /b 0
)

REM Safety: only kill if the pid still looks like a Research_native_loop.ps1 process.
set "IS_LOOP=0"
for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process -Filter ('ProcessId = %LOCK_PID%') -ErrorAction SilentlyContinue; if ($null -eq $p) { '' } else { $p.CommandLine }"`) do (
  set "PID_CMDLINE=%%L"
)
echo %PID_CMDLINE% | findstr /I "Research_native_loop.ps1" >nul 2>nul && set "IS_LOOP=1"

if "%IS_LOOP%"=="1" (
  echo [stop_research] Killing process tree pid=%LOCK_PID% ...
  taskkill /PID %LOCK_PID% /T /F >nul 2>nul
) else (
  echo [stop_research] PID=%LOCK_PID% is not a Research_native_loop.ps1 process anymore. Clearing stale lock only.
)

REM Always clear the lock afterwards (it may be stale).
cmd /c del /f /q "%LOCK_FILE%" >nul 2>nul
echo [stop_research] Done.
exit /b 0
