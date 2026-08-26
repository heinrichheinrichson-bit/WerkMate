# WerkMate 0.6.0 – Anleitung

Diese Anleitung beschreibt den aktuellen lokalen PC-Prototyp. Er eignet sich,
um den vollständigen Arbeitsablauf zu testen. Eine installierbare Android-App
ist dieser Stand noch nicht.

## 1. Voraussetzungen

- Windows-PC
- Python 3.11 oder neuer
- Für die tägliche Nutzung ist keine Internetverbindung erforderlich.

Python kann in PowerShell mit folgendem Befehl geprüft werden:

```powershell
py --version
```

## 2. WerkMate starten

Öffne im Windows-Explorer den Projektordner:

```text
F:\Eigene Apps\WerkMate
```

Starte anschließend die Datei:

```text
WerkMate starten.bat
```

Alternativ kann WerkMate aus PowerShell gestartet werden:

```powershell
cd "F:\Eigene Apps\WerkMate"
py start_werkmate.py
```

Beim ersten Start wird automatisch eine lokale Datenbank angelegt. Es ist kein
Benutzerkonto und keine Anmeldung erforderlich.

## 3. Einen Auftrag anlegen

1. Öffne den Reiter **Aufträge**.
2. Trage Auftragsnummer, Gesenknummer und Arbeitsgang ein.
3. Gib die ursprüngliche Auftragsmenge ein.
4. Gib die Vorgabezeit pro Stück ein. Kommazahlen wie `7,5` sind erlaubt.
5. Ergänze bei Bedarf eine allgemeine Auftragsnotiz.
6. Klicke auf **Auftrag anlegen**.

Der Auftrag erscheint danach in der Liste. Die Spalte **Offen/Gesamt** zeigt
beispielsweise `24/24`.

Ist die Gesenknummer bereits im Katalog vorhanden, kann sie aus der Liste
gewählt werden. WerkMate bietet danach nur die zugehörigen Arbeitsgänge an und
trägt deren aktuelle Vorgabezeit automatisch ein.

## 4. Gesenk- und Vorgabezeiten-Katalog pflegen

Öffne den Reiter **Gesenk-Katalog**. Für jede Kombination werden gespeichert:

- Gesenknummer und optionale Beschreibung
- Arbeitsgangcode, beispielsweise `FP1`
- verständliche Arbeitsgangbezeichnung
- aktuelle Vorgabezeit pro Stück
- optionale Notiz zum Gesenk

Eine bereits vorhandene Kombination aus Gesenk und Arbeitsgang wird beim
erneuten Speichern aktualisiert. Neue Aufträge erhalten danach die neue
Vorgabezeit. Bereits gespeicherte Aufträge und historische Meldungen verändern
sich dadurch nicht.

Nicht mehr benötigte Vorgaben können deaktiviert werden. Sie verschwinden aus
der Auswahl, ohne historische Daten zu löschen.

## 5. Einen Arbeitseinsatz starten

1. Markiere den gewünschten Auftrag in der Liste.
2. Gib bei **Menge** an, wie viele der offenen Stücke du jetzt bearbeiten willst.
3. Gib die gewünschte betriebliche Anmeldezeit ein. Das Format ist
   `JJJJ-MM-TT HH:MM`.
4. Wähle Schicht 1, 2 oder 3. Ohne Auswahl wird keine Pause und keine
   Reststückprognose bis Schichtende berechnet.
5. Klicke auf **Arbeit starten**.

WerkMate wechselt zum laufenden Auftrag und zeigt:

- Auftrags-, Gesenk- und Arbeitsgangnummer
- Menge und Vorgabezeit
- berechnetes Soll-Ende
- verbleibende Zeit beziehungsweise rote Überziehung
- laut Vorgabe vollständig mögliche Stücke bis Schichtende
- Überzeit, die das nächste Stück verursachen würde

Die feste Schichtpause wird nur abrechnungstechnisch berücksichtigt. Der Timer
wird nicht manuell eingefroren.

## 6. Sollzeit und Benachrichtigung

Solange WerkMate geöffnet ist, aktualisiert sich die Anzeige jede Sekunde. Beim
Erreichen der Sollzeit ertönt ein Signal und ein Warnfenster erscheint. Der
Arbeitseinsatz endet nicht automatisch. Die Überziehungszeit läuft weiter, bis
du bewusst rückmeldest.

Wichtig: Version 0.4.0 besitzt noch keine zuverlässige Windows-, Android- oder
iOS-Hintergrundbenachrichtigung. Das Warnfenster funktioniert nur, während das
Programm geöffnet ist.

## 7. Teilmenge oder Auftrag rückmelden

1. Trage bei **Fertige Stück** die von dir tatsächlich fertig bearbeitete Menge ein.
2. Trage die gewünschte Abmeldezeit ein oder klicke auf **Aktuelle Zeit**.
3. Ergänze bei Bedarf eine Meldungsnotiz.
4. Klicke auf **Rückmeldung speichern**.

Die Abmeldezeit darf vom Soll-Ende abweichen. Liegt sie vor der Anmeldezeit oder
mehr als 30 Minuten vom Soll-Ende entfernt, zeigt WerkMate eine Warnung. Die
Eingabe kann trotzdem bewusst bestätigt werden.

Beispiel:

- ursprüngliche Menge: 24 Stück
- persönlich fertiggemeldet: 20 Stück
- anschließend offen: 4 Stück

Der Auftrag bleibt als teilweise erledigt gespeichert. Die vier offenen Stücke
können an einem späteren Tag erneut gestartet werden.

## 8. Einen Restauftrag später fortsetzen

1. Öffne den Reiter **Aufträge**.
2. Markiere den teilweise erledigten Auftrag.
3. Trage die gewünschte Einsatzmenge ein – höchstens die offene Menge.
4. Trage die neue Anmeldezeit und Schicht ein.
5. Klicke auf **Arbeit starten**.

Jeder Arbeitseinsatz wird separat gespeichert. Dadurch bleiben verschiedene
Tage und Teilrückmeldungen nachvollziehbar.

## 9. Historie ansehen

Der Reiter **Historie** zeigt alle persönlichen Arbeitseinsätze mit:

- Datum
- Auftrag, Gesenk und Arbeitsgang
- gemeldeter An- und Abmeldezeit
- fertiggemeldeter Stückzahl
- Status

Ein Doppelklick auf einen Eintrag öffnet weitere Details einschließlich
Soll-Ende und Notiz.

Die Suche findet Auftragsnummern, Gesenknummern, Arbeitsgänge und Notiztexte.
Zusätzlich kann die Liste nach Meldungsstatus gefiltert werden.

## 10. Gespeicherte Aufträge korrigieren

Markiere einen Auftrag und klicke auf **Auftrag bearbeiten** oder doppelklicke
auf seine Tabellenzeile. Gesenknummer, Arbeitsgang, Gesamtmenge, aktuelle
Vorgabezeit und Auftragsnotiz können geändert werden.

Historische Arbeitseinsätze behalten ihre damals gespeicherte Vorgabezeit. Über
**Änderungen anzeigen** bleibt nachvollziehbar, wann welcher Auftragswert
korrigiert wurde.

Ein abgegebener Restauftrag kann markiert und mit **Abgegebenen Auftrag wieder
aufnehmen** erneut in die persönliche Bearbeitung übernommen werden.

## 11. Wo liegen die Daten?

Die lokale Datenbank liegt standardmäßig hier:

```text
%LOCALAPPDATA%\WerkMate\werkmate.sqlite3
```

Unter einem typischen Windows-Benutzerkonto entspricht das ungefähr:

```text
C:\Users\DEIN-NAME\AppData\Local\WerkMate\werkmate.sqlite3
```

Die Daten werden nicht automatisch zu GitHub oder in eine Cloud übertragen.

## 12. Datensicherung

Klicke oben rechts auf **Daten sichern**, wähle einen Zielordner und speichere
die vorgeschlagene `.sqlite3`-Datei. WerkMate erzeugt eine konsistente Kopie
der gesamten lokalen Historie.

Alternativ ist eine manuelle Sicherung möglich:

1. WerkMate vollständig schließen.
2. Die Datei `werkmate.sqlite3` aus dem oben genannten Ordner kopieren.
3. Die Kopie an einem sicheren Ort ablegen.

Zur Wiederherstellung WerkMate schließen und die gesicherte Datei wieder an
denselben Ort kopieren. Eine komfortable Sicherungsfunktion in der Oberfläche
ist für eine spätere Version vorgesehen.

## 13. Bekannte Grenzen dieses Stands

- noch keine Android- oder iOS-App
- keine zuverlässige Benachrichtigung bei geschlossenem Programm
- noch keine Wiederherstellung einer Sicherung direkt in der Oberfläche
- Arbeitseinsätze können noch nicht nachträglich in der Oberfläche korrigiert werden
- keine Statistiken und Exporte

Der Rechenkern, die lokale Speicherung und der grundlegende persönliche Ablauf
sind bereits vorhanden und automatisiert getestet.

## 14. Optionale Konsolenbedienung

Die bisherige Konsolenoberfläche bleibt erhalten. Ihre Befehle sind in
[`KONSOLEN-MVP.md`](KONSOLEN-MVP.md) dokumentiert.
