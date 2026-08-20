@echo off
setlocal

rem Double-click launcher: choose a project, then open the learner-first Atlas.
set "SKILL_ROOT=%~dp0.."
set "PYTHONPATH=%SKILL_ROOT%\src;%PYTHONPATH%"

if not "%~1"=="" (
    set "PROJECT=%~f1"
) else (
    for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $dialog = New-Object System.Windows.Forms.FolderBrowserDialog; $dialog.Description = 'Chon thu muc project de hieu codebase'; if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Write($dialog.SelectedPath) }"`) do set "PROJECT=%%I"
)

if not defined PROJECT exit /b 0

py -3 -m excaliflow.cli open --dir "%PROJECT%"
if errorlevel 1 pause
endlocal
