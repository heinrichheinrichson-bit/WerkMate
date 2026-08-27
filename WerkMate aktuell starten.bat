@echo off
cd /d "%~dp0"
set "WERKMATE_CURRENT=%~dp0dist\WerkMate-aktuell\WerkMate-aktuell.exe"
if not exist "%WERKMATE_CURRENT%" (
  echo Die aktuelle portable WerkMate-Version wurde noch nicht gebaut.
  echo Erwartet: %WERKMATE_CURRENT%
  pause
  exit /b 1
)
start "" "%WERKMATE_CURRENT%"
