# WerkMate

WerkMate ist ein lokaler, persönlicher Assistent für Aufträge, Schichten und
Vorgabezeiten. Er berechnet Soll-Endzeiten, feste verrechenbare Pausen,
Reststücke und Überziehungen. Persönliche Teilrückmeldungen, Notizen und eine
Historie bleiben lokal auf dem Gerät.

## Entwicklungsstand

**Version 0.12.0 – verkettete Schichtplanung für Aufträge und Guthaben**

Die erste Version konzentriert sich auf eine eindeutig getestete Fachlogik.
Eine mobile Oberfläche für Android und später iOS wird auf diesen Rechenkern
aufgesetzt.

## Lokale Entwicklung

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
werkmate --help
werkmate-gui
```

WerkMate benötigt für den Rechenkern keine Internetverbindung und keine Cloud.

## Versionsschema

Das Projekt verwendet [Semantic Versioning](https://semver.org/):

- `0.1.x`: Rechenkern und Tests
- `0.2.x`: lokale Aufträge, Meldungen und Historie
- `0.3.x`: bedienbarer lokaler MVP
- `1.0.0`: erster stabiler mobiler Alltagsstand

Zum direkten Ausprobieren unter Windows kann außerdem `WerkMate starten.bat`
im Projektordner doppelt angeklickt werden.

Siehe [Anleitung](docs/ANLEITUNG.md),
[MVP-Spezifikation](docs/MVP-SPEZIFIKATION.md),
[Konsolen-MVP ausprobieren](docs/KONSOLEN-MVP.md) und
[Änderungen](CHANGELOG.md).
