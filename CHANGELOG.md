# Änderungsverlauf

Alle wesentlichen Änderungen werden in dieser Datei dokumentiert.

## [Unveröffentlicht]

## [0.30.0] - 2026-08-27

### Schichtplanung

- Technische Reihenfolgentabelle durch direkt bedienbare Auftragskarten ersetzt
- Jede Karte zeigt geplanten Start, geplantes Ende, Stückzahl, Stückzeit, Dauer und Restmenge
- Scrollbare Tageszeitleiste für beliebig viele geplante Arbeiten
- Reihenfolge direkt per Ziehgriff oder weiterhin über Pfeiltasten änderbar
- Bearbeiten, Duplizieren und Entfernen unmittelbar am jeweiligen Auftrag
- Startzeit des ersten Auftrags und optionales längeres Schichtende klarer benannt
- Normales Schichtende bleibt automatisch; zusätzliche Arbeitszeit wird nur bewusst eingetragen
- Manueller Auftrag und noch nicht gespeicherter Auftrag teilen denselben Eingabedialog
- Stückzeit wird bei einer eindeutigen Gesenk-/Arbeitsgang-Kombination aus dem Katalog übernommen
- Planung wird nach Ergänzen, Bearbeiten, Duplizieren, Entfernen oder Umordnen neu berechnet

### Klarheit und Sicherheit

- Dauerhaft sichtbarer Hinweis, dass Folgezeiten nur geplant sind
- Startknopf ausdrücklich als manueller Start des ersten Auftrags bezeichnet
- Kein Auftrag startet durch Berechnung, Umordnung oder Ablauf einer geplanten Zeit automatisch

### Qualität

- GUI-Prüfung der Zeitkette `05:45 → 06:45 → 06:45`
- GUI-Prüfung der Drag-and-drop-Neuberechnung mit mehreren Aufträgen
- Alle 83 automatisierten Tests bestanden

## [0.29.0] - 2026-08-27

### Oberfläche

- Laufender Arbeitstag als scrollbar aufgebautes Dashboard für kleinere Fenster und Tablets
- Startzeit, geplantes Ende und Fortschritt bleiben als erste Kennzahlen sichtbar
- Aktueller und nächster Arbeitsschritt stehen direkt nebeneinander
- Countdown, Fortschrittsbalken und geplante Rückmeldezeit bilden eine gemeinsame Hauptkarte
- Prognose und Restmenge sind als nachgeordnete Informationen zusammengefasst
- Größere Abstände, Touch-Schaltflächen und eine klarere aktive Tab-Markierung
- Breiteres Standardfenster bei weiterhin nutzbarer Mindestgröße

### Sicherheit und Qualität

- Rückmelde-, Abbruch- und Verlängerungszustände bleiben von der optischen Umstellung getrennt
- Leerer und aktiver Dashboard-Zustand manuell geprüft
- Alle 83 automatisierten Tests bestanden

## [0.28.0] - 2026-08-27

### Neu

- Eigener Wechselbildschirm nach Rückmeldung des aktuellen Auftrags
- Zusammenfassung von geplantem und tatsächlichem Ende sowie Zeitabweichung
- Nächster Auftrag mit aktualisiertem Start, Ende und Stückzahl
- Getrennte Entscheidungen „Noch nicht starten“ und „Nächsten Auftrag jetzt starten“
- Sichtbarer roter Alarmzustand nach Ablauf der Sollzeit
- Roter Fortschrittsbalken bei überfälliger Rückmeldung
- Erneute akustische Erinnerung nach drei Minuten frei auslösbar

### Sicherheit

- Ein Folgeauftrag startet niemals allein durch Countdown, Alarm oder Rückmeldung
- Erst der ausdrückliche Klick im Wechselbildschirm startet den nächsten Countdown
- Verlängerung setzt Alarm und Wiederholung auf die neue Endzeit zurück

### Qualität

- GUI-Test beweist: nach Rückmeldung kein aktiver Auftrag bis zur manuellen Bestätigung
- GUI-Test beweist: Alarmzustand löst keinen Auftragswechsel aus

## [0.27.0] - 2026-08-27

### Neu

- Tagesmonitor im Reiter „Laufender Auftrag“
- Startzeit, geplantes Ende und Fortschritt als große Kennzahlen auf den ersten Blick
- Bereich „Als Nächstes“ mit Folgeauftrag, geplantem Start, Ende und Stückzahl
- Vollständiger aktueller Tagesablauf als verbundene, scrollbar angeordnete Auftragskarten
- Aktiver und geplanter Auftrag werden im Ablauf eindeutig unterschieden
- Tagesablauf ist auch vor dem Start des ersten Planpunkts sichtbar

### Verbessert

- Rückmeldebereich steht optisch nach den zentralen Zeit- und Ablaufdaten
- Folgezeiten werden aus dem aktuellen Zielende und dem gespeicherten Schichtplan berechnet
- Überholte manuelle Startvorgaben vor dem aktuellen Ende blockieren die Vorschau nicht

### Qualität

- GUI-Ablauftest mit aktuellem Auftrag `05:45–06:45` und Folgeauftrag ab `06:45`

## [0.26.0] - 2026-08-27

### Neu

- Auslastungsbalken für die produktive Schichtkapazität
- Verständlicher Status: Schicht gefüllt, nahezu gefüllt, freie Zeit oder Überzeit
- Direkte Kartenaktionen für Bearbeiten, Duplizieren, Verschieben und Entfernen
- Bearbeitungsdialog für Planungsart, Menge/Minuten und abweichende Startzeit
- Jede Änderung an Reihenfolge, Menge oder Startzeit berechnet den Ablauf sofort neu
- Schutz vor mehrfacher Überplanung derselben offenen Auftragsmenge

### Verbessert

- Gesamtübersicht zeigt geplante, verfügbare und freie produktive Zeit getrennt
- Leerer Plan wird nach dem letzten Entfernen sauber verworfen
- Folgezeiten bleiben nach Drag-and-drop und Pfeilverschiebung unmittelbar aktuell

### Qualität

- Test gegen doppelte Einplanung über die offene Auftragsmenge hinaus
- GUI-Test für Zeitkette, Auslastung, Restzeit-Status und Kartenaktionen

## [0.25.1] - 2026-08-27

### Verbessert

- Planbeginn wird einmal zentral eingetragen und gilt für den ersten Auftrag
- Folgeaufträge erhalten automatisch die Endzeit des vorherigen Auftrags als Startzeit
- Schichtablauf wird nach jedem hinzugefügten Auftrag sofort neu berechnet und angezeigt
- Abweichende Einzelstartzeit ist deutlicher als seltene Ausnahme gekennzeichnet
- Manueller Planauftrag besitzt eine sichtbare Abbrechen-Schaltfläche
- Erklärung des automatischen Zeitablaufs direkt oberhalb der Planpunkte
- Eindeutige temporäre Auftragsnummern auch bei sehr schnell hintereinander angelegten Planpunkten

### Qualität

- Fach- und GUI-Test für 10 Stück à 6 Minuten: `05:45–06:45`, Folgeauftrag ab `06:45`

## [0.25.0] - 2026-08-27

### Neu

- Standardplanung begrenzt jeden Auftrag auf die verbleibende produktive Schichtzeit
- Anzeige der für heute vollständig möglichen und rechnerischen Stückzahl
- Anzeige der nach dem Tagesplan weiterhin offenen Auftragsmenge
- Anzeige von belegter, verfügbarer und noch freier produktiver Schichtzeit
- Optionales heutiges Schichtende für bewusst geplante Überstunden
- Abweichendes Schichtende wird mit dem Schichtplan lokal gespeichert
- Bewusste feste Stückplanung über das Schichtende hinaus bleibt als eigene Planungsart erhalten
- Automatische Datenbankmigration auf Schema-Version 11

### Qualität

- Tests für 48 Stück à 20 Minuten: normal 23 Stück, mit verlängertem Ende 29 Stück
- Tests für Restkapazität, Folgeauftrag und gespeichertes abweichendes Schichtende

## [0.24.1] - 2026-08-26

### Verbessert

- Im Schichtplan genügt für Planstart und eigene Startzeiten die Uhrzeit `HH:MM`
- Das aktuelle Datum wird automatisch verwendet
- Beim Bearbeiten wird nur noch die kurze Uhrzeit angezeigt
- Verständlicher Eingabehinweis mit Beispiel `13:45`
- Vollständige Datums- und Zeitangaben bleiben optional kompatibel

## [0.24.0] - 2026-08-26

### Behoben

- Manueller Planauftrag wird nach gültiger Eingabe zuverlässig angelegt und der Dialog geschlossen
- Kurze Uhrzeiten wie `13:45` werden relativ zum Plantag korrekt verarbeitet
- Stückzeit wird bei bekannter Gesenk-/Arbeitsgang-Kombination automatisch aus dem Katalog übernommen
- Bei genau einem Katalog-Arbeitsgang genügt die Gesenknummer; Arbeitsgang und Stückzeit werden ergänzt
- Bei mehreren Arbeitsgängen zeigt WerkMate die vorhandenen AG-Codes als Auswahlhilfe
- Für „Offene Stück fest“ ist keine zusätzliche Zahl mehr nötig; leer bedeutet alle offenen Stück
- Das mehrdeutige Feld „Stück/Minuten“ erhält je nach Planungsart eine eindeutige Beschriftung

### Qualität

- Erweiterte Tests für kurze und vollständige Planstartzeiten
- Vollständige Logik-, Syntax-, Datenbank- und GUI-Ablaufprüfung

## [0.23.0] - 2026-08-26

### Neu

- Waagerechter Zeitfortschrittsbalken für den aktiven Auftrag
- Frei wählbare neue Endzeit über „Brauche länger“
- Garantierter erneuter Alarm nach jeder Verlängerung
- Vollständiges Verlängerungsprotokoll mit alter/neuer Endzeit und Grund
- Direkte manuell bestätigte Anmeldung des nächsten Planauftrags nach Rückmeldung
- Kein automatischer Wechsel zwischen Aufträgen
- Auch laufende und abgebrochene Historieneinträge können sicher storniert werden
- Laufende Einträge werden beim Verschieben in den Papierkorb zuverlässig beendet
- Automatische Datenbankmigration auf Schema-Version 10

## [0.22.0] - 2026-08-26

### Neu

- Reihenfolge der Planpunkte per Drag & Drop ändern
- Zusätzliche Pfeiltasten für präzise und touchfreundliche Sortierung
- Zukünftige Aufträge während eines laufenden Planpunkts einfügen und umsortieren
- Aktiver Auftrag bleibt vor versehentlichem Verschieben geschützt
- Aktualisierte Restplanung zunächst ab dem geplanten, später ab dem tatsächlichen Ende

## [0.21.0] - 2026-08-26

### Neu

- Erste visuelle Schichtablauf-Timeline mit verbundenen Auftragskarten
- Manuelle Planaufträge ohne vorhandenen Katalog- oder Auftragsdatensatz
- Wahlweise nur im Ablauf verwenden oder dauerhaft als Auftrag speichern
- Optionale feste Startzeit für jeden einzelnen Planpunkt
- Getrennte Anzeige von gesamter Ablaufzeit und produktiver Gesamtvorgabezeit
- Persistenz der manuellen Startvorgaben über Programmneustarts
- Automatische Datenbankmigration auf Schema-Version 8

## [0.20.0] - 2026-08-26

### Neu

- Aufträge duplizieren und Kopien direkt anpassen
- Auftragsnummern und unvollständige Schnellstartdaten nachträglich ergänzen
- Auftrags-Papierkorb mit Wiederherstellen und endgültigem Löschen
- Rückmeldungen stornieren, ohne Mengen oder Guthaben weiter zu beeinflussen
- Getrennter Storno-Papierkorb mit Wiederherstellung und endgültiger Bereinigung
- Normale Auftrags- und Historienlisten bleiben frei von archiviertem Testmüll
- Automatische Datenbankmigration auf Schema-Version 7

## [0.19.0] - 2026-08-26

### Neu

- Erster echter Flutter-Prototyp für Android und später iOS
- Mobiler Schnellstart mit minimalen Pflichtangaben
- Schichtprognose inklusive fester Pausen und Dezimalstückzahl
- Mobile Ansicht für laufenden Einsatz und geplante Rückmeldezeit
- Getrennte Rückmeldung von bearbeiteten und betrieblich gemeldeten Stück
- Einfache mobile Historie mit Guthabenänderung
- Installierbare Android-Release-APK lokal erfolgreich gebaut

## [0.18.0] - 2026-08-26

### Neu

- Eigenständige Windows-EXE ohne separat erforderliche Python-Installation
- Reproduzierbares PyInstaller-Buildskript per Doppelklick
- Versionierte Build-Konfiguration und eigene Windows-Anleitung
- Programmdaten bleiben unabhängig von der EXE unter LocalAppData erhalten

## [0.17.0] - 2026-08-26

### Neu

- Eigener kompakter Reiter für persönliche Auswertungen
- Umschaltung zwischen heutigem Tag und laufender Woche
- Summen für Einsätze, bearbeitete und gemeldete Stück sowie Guthabenänderung
- Zusammengefasste Zeit- und Stückabweichung mit verständlicher Grün-/Rot-Anzeige
- Tageszeilen zur schnellen Nachvollziehbarkeit ohne überladene Diagramme

## [0.16.0] - 2026-08-26

### Neu

- Lokale Sicherungen können direkt in der Oberfläche wiederhergestellt werden
- Integritäts- und WerkMate-Prüfung vor jeder Wiederherstellung
- Automatische Sicherheitskopie des aktuellen Stands vor dem Ersetzen
- Excel-tauglicher CSV-Export der Aufträge und vollständigen Rückmeldungshistorie
- Seltene Datenwerkzeuge übersichtlich im Reiter Einstellungen gebündelt

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
