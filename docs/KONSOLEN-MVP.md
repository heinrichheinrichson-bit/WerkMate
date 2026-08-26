# WerkMate 0.3 – Konsolen-MVP ausprobieren

Der Konsolen-MVP ist eine bewusst einfache Testoberfläche für den fachlichen
Ablauf. Die Daten werden standardmäßig unter
`%LOCALAPPDATA%\WerkMate\werkmate.sqlite3` gespeichert.

## Installation

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Beispielablauf

```powershell
werkmate auftrag-neu --nummer FA-4711 --gesenk 8720 --arbeitsgang FP1 --menge 24 --minuten 20 --notiz "Besonderer Auftrag"

werkmate auftraege

werkmate start --auftrag 1 --menge 24 --anmeldung "2026-08-26 13:45" --schicht 2

werkmate status

werkmate rueckmelden --einsatz 1 --stueck 20 --abmeldung "2026-08-26 21:45" --notiz "Vier Stück bleiben offen"

werkmate historie
```

Eine Abmeldezeit, die vor der Anmeldung oder mehr als 30 Minuten vom Soll-Ende
entfernt liegt, erzeugt eine Warnung. Sie bleibt erlaubt und kann bewusst mit
`--bestaetigen` übernommen werden.

Ein Restauftrag kann später erneut mit `werkmate start` aufgenommen oder mit
folgendem Befehl aus der persönlichen Nachverfolgung abgegeben werden:

```powershell
werkmate abgeben --auftrag 1 --grund "Kollege übernimmt den Rest"
```

Eine alternative Testdatenbank kann global angegeben werden:

```powershell
werkmate --db .\test.sqlite3 auftraege
```

