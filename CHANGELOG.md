# Änderungsverlauf

Alle wesentlichen Änderungen werden in dieser Datei dokumentiert.

## [Unveröffentlicht]

## [0.15.0] - 2026-08-26

### Neu

- Abgeschlossene Rückmeldungen können direkt in der Historie korrigiert werden
- Korrigierbar sind An-/Abmeldezeit, beide Stückzahlen und die Notiz
- Pflichtfeld für einen nachvollziehbaren Korrekturgrund
- Unveränderliches Protokoll mit altem Wert, neuem Wert, Zeitpunkt und Grund
- Automatische Neuberechnung von offener Menge, Guthaben und Abweichungen
- Schutz vor unmöglichen Gesamtmengen und negativem Auftragsguthaben

## [0.14.0] - 2026-08-26

### Neu

- Eigener übersichtlicher Reiter für Schicht- und Pauseneinstellungen
- Beginn, Ende und eine feste Pause sind für alle drei Schichten lokal einstellbar
- Nachtschichten über Mitternacht werden automatisch erkannt
- Ungültige Zeiten und Pausen außerhalb der Schicht werden verhindert
- Automatische Schichterkennung berücksichtigt die persönlichen Einstellungen
- Standardzeiten können mit einem Klick wieder in das Formular eingesetzt werden
- Automatische Datenbankmigration auf Schema-Version 6

## [0.13.0] - 2026-08-26

### Neu

- Schichtpläne werden dauerhaft in der lokalen SQLite-Datenbank gespeichert
- Restpläne werden nach einem Neustart automatisch geladen
- Folgende Planpunkte werden ab der tatsächlichen Rückmeldezeit neu berechnet
- Nach einer Rückmeldung wird der nächste aktualisierte Planpunkt angeboten
- Abgebrochene Fehlstarts werden wieder in den offenen Plan zurückgelegt
- Automatische Datenbankmigration auf Schema-Version 5

## [0.12.1] - 2026-08-26

### Geändert

- Arbeitsgangbezeichnung im Gesenk-Katalog ist nicht mehr verpflichtend
- Leere Bezeichnung wird automatisch mit dem AG-Code gefüllt
- Pflicht sind nur Gesenknummer, AG-Code und Vorgabezeit
- Optionale Felder sind in der Oberfläche eindeutig gekennzeichnet

## [0.12.0] - 2026-08-26

### Hinzugefügt

- Verkettete Planung mehrerer Aufträge in frei gewählter Reihenfolge
- Feste Restmenge eines Auftrags vor einem zweiten Auftrag
- Automatisches Füllen der verbleibenden Schicht mit vollständigen Stücken
- Guthabenblöcke nach Stück oder Minuten innerhalb desselben Schichtplans
- Fortlaufende Pausenberechnung über alle Planpunkte
- Start, Ende, Dezimalstückzahl, vollständige Stück und Überzeit je Planpunkt
- Direkter Start des ersten berechneten Planpunkts
- Übernahme des geplanten Endes als Start für die verbleibende Reihenfolge

## [0.11.0] - 2026-08-26

### Hinzugefügt

- Getrennte Speicherung tatsächlich bearbeiteter und betrieblich rückgemeldeter Stück
- Guthaben je Auftrag, Gesenk und Arbeitsgang in Stück, Minuten und Stunden
- Sichtbare Werte für Bearbeitet, Rückgemeldet, Guthaben und noch zu bearbeiten
- Guthaben-Anmeldung nach frei gewählter ganzer Stückzahl
- Guthaben-Anmeldung nach exakt vorgegebener produktiver Zeit
- Dezimalstückzahl und normaler Rundungsvorschlag bei einer Zeitvorgabe
- Freie endgültige Stückentscheidung beim Abmelden des Guthabens
- Mehrtägiger, stückweiser Verbrauch eines Guthabens
- Guthabenzeit belegt die Schicht und bestimmt den Start des nächsten Auftrags
- Automatische Migration bestehender Rückmeldungen auf Datenbankschema 4

## [0.10.0] - 2026-08-26

### Hinzugefügt

- Gesamtvorgabezeit eines Auftrags in Minuten und Stunden/Minuten
- Live-Berechnung der Gesamtvorgabezeit bei der Auftragseingabe
- Geplante und tatsächlich gemeldete Stückzahl in der Historie
- Zeitabweichung gegenüber der geplanten Rückmeldung in Minuten und Prozent
- Stückabweichung gegenüber der geplanten Einsatzmenge als Anzahl und Prozent
- Rote Kennzeichnung für Verzug und weniger Stück
- Grüne Kennzeichnung für frühere Rückmeldung und mehr Stück
- Neutrale Darstellung bei exakter Erfüllung
- Keine Leistungswertung für laufende oder abgebrochene Einsätze

## [0.9.0] - 2026-08-26

### Hinzugefügt

- Schnellstart mit Gesamtmenge plus manueller Stückzeit
- Schnellstart mit Gesenknummer und automatisch geladener Katalogvorgabe
- Automatische Arbeitsgangwahl, wenn nur eine Vorgabe zum Gesenk existiert
- Eindeutige Schnellauftragsnummer, falls keine Auftragsnummer eingegeben wird
- Automatische Schicht- und Anmeldezeitvorauswahl
- Automatisch empfohlene persönliche Einsatzmenge innerhalb der Restschicht

### Geändert

- Abstrakte Anzeige „Nächstes Stück: +00:05:00 Überzeit“ durch Klartext ersetzt
- Zusätzliche Stückprognose nennt konkrete Fertigzeit und Minuten nach Schichtende
- Überzeit-Hinweis wird als optionale Entscheidungshilfe erklärt

## [0.8.0] - 2026-08-26

### Hinzugefügt

- Klare Trennung zwischen Teilrückmeldung und vollständigem Auftragsabschluss
- Vollständiger Abschluss meldet bewusst alle noch offenen Stück
- Fehlstart kann ohne Stückmeldung abgebrochen und anschließend neu eingegeben werden
- Abgebrochene Einsätze bleiben nachvollziehbar in der Historie
- Weniger dominante Anzeige der gesamten offenen Vorgabezeit
- Anzeige, wie viel Vorgabezeit über die aktuelle Schichtkapazität hinausgeht

## [0.7.1] - 2026-08-26

### Geändert

- Große Gesamtaufträge werden nicht mehr automatisch als ein durchgehender Einsatz behandelt
- Einsatzmenge wird mit den vollständig möglichen Stücken der Restschicht vorbelegt
- „Soll-Ende“ wurde als geplante Rückmeldezeit für die Einsatzmenge verständlich gemacht
- Schichtprognose basiert dauerhaft auf der Anmeldezeit und verändert sich nicht sekündlich
- Warnung, wenn bewusst mehr Stück als innerhalb der Restschicht möglich gestartet werden
- Countdown und Warntext beziehen sich auf die geplante Rückmeldung statt den Gesamtauftrag

## [0.7.0] - 2026-08-26

### Hinzugefügt

- Automatische Sollstückzahl aus Anmeldezeit, Schichtende, Pause und Vorgabezeit
- Dezimale Sollleistung, beispielsweise `23,1 Stück`
- Separate Anzeige vollständig fertigstellbarer Stücke
- Restzeit im nächsten Stück und notwendige Überzeit zur Fertigstellung
- Offene Restmenge nach Schichtende
- Automatische Aktualisierung bei Auftrag-, Schicht- oder Zeitwahl
- Automatische Vorauswahl der aktuell laufenden Standardschicht
- Begrenzung der Prognose auf die offene Auftragsmenge

## [0.6.0] - 2026-08-26

### Hinzugefügt

- Gesenk-Katalog mit Beschreibung und Notiz
- Frei verwaltbare Arbeitsgangcodes und Bezeichnungen
- Aktuelle Vorgabezeit je Kombination aus Gesenk und Arbeitsgang
- Suche nach Gesenk, Beschreibung, Arbeitsgangcode und Arbeitsgangname
- Aktualisierung und Deaktivierung von Vorgaben ohne Verlust historischer Daten
- Automatische Vorschläge und Zeitübernahme beim Anlegen eines Auftrags
- Automatische lokale Datenbankmigration auf Schema-Version 3

## [0.5.0] - 2026-08-26

### Hinzugefügt

- Bearbeitungsmaske für Gesenk, Arbeitsgang, Gesamtmenge, Vorgabezeit und Notiz
- Dauerhaftes Änderungsprotokoll direkt aus der Auftragsansicht
- Wiederaufnahme zuvor abgegebener Restaufträge
- Suche in Meldungen, Aufträgen, Gesenken, Arbeitsgängen und Notizen
- Statusfilter in der persönlichen Historie
- Schutz vor einer Gesamtmenge unterhalb bereits gemeldeter Stückzahlen
- Bestehende Arbeitseinsätze behalten ihre ursprüngliche Vorgabezeit

## [0.4.0] - 2026-08-26

### Hinzugefügt

- Grafische Windows-Testoberfläche mit drei übersichtlichen Bereichen
- Auftragserfassung und Start eines persönlichen Arbeitseinsatzes
- sekundengenauer Live-Countdown und rote Überziehungsanzeige
- Warnfenster beim Erreichen der Sollzeit, solange das Programm geöffnet ist
- Teilrückmeldung mit frei gewählter Abmeldezeit und Notiz
- Auftragsliste mit offenen Mengen und persönliche Historie
- Detailansicht für historische Meldungen
- Übergabe eines offenen Restauftrags über die Oberfläche
- Konsistente lokale Datenbanksicherung über einen Dateidialog
- Windows-Startdatei und ausführliche deutschsprachige Bedienungsanleitung

## [0.3.0] - 2026-08-26

### Hinzugefügt

- Bedienbarer deutscher Konsolen-MVP
- Befehle für Auftrag, Start, Live-Status, Teilrückmeldung, Historie und Übergabe
- Warnung mit bewusster Bestätigung bei auffälligen Abmeldezeiten
- Prognose vollständiger Stücke und Überzeit des nächsten Stücks
- Dokumentierter Beispielablauf
- Automatische Migration der lokalen Datenbank auf Schema-Version 2

## [0.2.0] - 2026-08-26

### Hinzugefügt

- Lokale SQLite-Datenbank mit Schema-Version
- Aufträge, persönliche Arbeitseinsätze und Teilrückmeldungen
- Fortsetzbare Restmengen und Status „abgegeben“
- Auftrags- und Meldungsnotizen
- Historie und nachvollziehbares Korrekturprotokoll

## [0.1.0] - 2026-08-26

### Hinzugefügt

- Unabhängiger Rechenkern für Vorgabezeit, Pausen, Schichten und Restmengen
- Automatisierte fachliche Tests
