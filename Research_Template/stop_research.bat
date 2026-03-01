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

echo [stop_research] Killing process tree pid=%LOCK_PID% ...
taskkill /PID %LOCK_PID% /T /F >nul 2>nul

REM Always clear the lock afterwards (it may be stale).
cmd /c del /f /q "%LOCK_FILE%" >nul 2>nul
echo [stop_research] Done.
exit /b 0

