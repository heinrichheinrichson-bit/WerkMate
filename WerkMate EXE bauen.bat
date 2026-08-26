@echo off
cd /d "%~dp0"
echo WerkMate wird als eigenstaendige Windows-EXE gebaut ...
py -m PyInstaller --noconfirm --clean WerkMate.spec
if errorlevel 1 (
  echo.
  echo Der EXE-Build ist fehlgeschlagen.
  pause
  exit /b 1
)
echo.
echo Fertig: %~dp0dist\WerkMate.exe
pause
