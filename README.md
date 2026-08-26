# WerkMate

WerkMate ist ein lokaler, persönlicher Assistent für Aufträge, Schichten und
Vorgabezeiten. Er berechnet Soll-Endzeiten, feste verrechenbare Pausen,
Reststücke und Überziehungen. Persönliche Teilrückmeldungen, Notizen und eine
Historie bleiben lokal auf dem Gerät.

## Entwicklungsstand

**Version 0.3.0 – bedienbarer lokaler Konsolen-MVP**

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
```

WerkMate benötigt für den Rechenkern keine Internetverbindung und keine Cloud.

## Versionsschema

Das Projekt verwendet [Semantic Versioning](https://semver.org/):

- `0.1.x`: Rechenkern und Tests
- `0.2.x`: lokale Aufträge, Meldungen und Historie
- `0.3.x`: bedienbarer lokaler MVP
- `1.0.0`: erster stabiler mobiler Alltagsstand

Siehe [MVP-Spezifikation](docs/MVP-SPEZIFIKATION.md),
[Konsolen-MVP ausprobieren](docs/KONSOLEN-MVP.md) und
[Änderungen](CHANGELOG.md).
