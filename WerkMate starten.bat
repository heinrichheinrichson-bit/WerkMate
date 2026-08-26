@echo off
cd /d "%~dp0"
py start_werkmate.py
if errorlevel 1 (
  echo.
  echo WerkMate konnte nicht gestartet werden.
  echo Bitte pruefen, ob Python 3.11 oder neuer installiert ist.
  pause
)
