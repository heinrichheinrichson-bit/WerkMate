@echo off
cd /d "%~dp0"
set "WERKMATE_SIMPLE=%~dp0dist\WerkMate-Simple-0.5-portable\WerkMate-Simple-0.5-portable.exe"
if not exist "%WERKMATE_SIMPLE%" (
  echo WerkMate Simple wurde noch nicht gebaut.
  echo Erwartet: %WERKMATE_SIMPLE%
  pause
  exit /b 1
)
start "" "%WERKMATE_SIMPLE%"
