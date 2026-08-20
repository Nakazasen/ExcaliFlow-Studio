@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0ExcaliFlow-Setup.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not complete. Read the message above and try again.
  pause
)
