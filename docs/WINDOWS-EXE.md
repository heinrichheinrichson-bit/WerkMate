# WerkMate als Windows-EXE

Die fertige Datei `dist\WerkMate.exe` startet ohne separat installiertes Python.
Aufträge, Einstellungen und Historie liegen weiterhin unabhängig vom Programm
unter `%LOCALAPPDATA%\WerkMate\werkmate.sqlite3`.

## EXE neu bauen

1. Python und PyInstaller müssen installiert sein.
2. Im Projektordner `WerkMate EXE bauen.bat` doppelklicken.
3. Nach erfolgreichem Build liegt die neue Datei unter `dist\WerkMate.exe`.

Alternativ in PowerShell:

```powershell
py -m PyInstaller --noconfirm --clean WerkMate.spec
```

Der Build-Ordner und die EXE werden nicht in Git eingecheckt. Sie können jederzeit
reproduzierbar aus dem versionierten Quellcode erzeugt werden.
