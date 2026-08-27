# WerkMate – Stabilisierungsplan

Ab Version 0.31.1 werden vorerst keine neuen Module und keine zusätzlichen
Sonderfunktionen gebaut. Zuerst muss ein kleiner Kernablauf zuverlässig und
verständlich funktionieren.

## Verbindlicher Kernablauf

1. Auftrag mit Menge und Stückzeit erfassen oder auswählen.
2. Eine konkrete zukünftige oder aktuelle Schicht wählen.
3. Aufträge für diese Schicht in eine Reihenfolge bringen.
4. Ersten Auftrag ausdrücklich starten.
5. Sollzeit, Alarm und Überzeit korrekt anzeigen.
6. Auftrag vollständig oder teilweise rückmelden.
7. Nächsten Auftrag ausschließlich nach Bestätigung starten.
8. Alle Schritte später in der Historie nachvollziehen.

## Reihenfolge der Stabilisierung

1. Schicht- und Datumswahl, besonders Nachtschichten über Mitternacht
2. Stück- und Zeitberechnung des Schichtplans
3. Start, Countdown, Alarm und Verlängerung
4. Teilrückmeldung, Abschluss und manuelle Zeitkorrektur
5. Übergang zum nächsten geplanten Auftrag
6. Historie und Wiederherstellung nach App-Neustart

## Vorläufig nicht erweitern

- keine neuen Auswertungen
- keine Vorgesetztenfunktionen
- keine weiteren Sonderfälle für Guthaben
- keine zusätzliche optische Umgestaltung der PC-Oberfläche
- keine neuen Verwaltungsfunktionen

Jeder Punkt wird mit einem konkreten Beispielszenario geprüft. Erst wenn der
gesamte Kernablauf stabil ist, wird die Flutter-Oberfläche weiter ausgebaut.
