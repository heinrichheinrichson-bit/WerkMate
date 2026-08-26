# WerkMate 0.22.0 – Anleitung

Diese Anleitung beschreibt den aktuellen lokalen PC-Prototyp. Er eignet sich,
um den vollständigen Arbeitsablauf zu testen. Eine installierbare Android-App
liegt jetzt als erster getrennter Flutter-Prototyp unter `mobile` vor. Die
vollständige PC-Funktionalität und dauerhafte mobile Speicherung folgen später.

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

Wenn `dist\WerkMate.exe` vorhanden ist, kann WerkMate auch direkt darüber ohne
separat installiertes Python gestartet werden. Die persönlichen Daten sind in
beiden Startvarianten dieselben. `WerkMate EXE bauen.bat` erzeugt eine neue EXE.

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
beispielsweise `24/24`. Während der Eingabe und in der Auftragsliste zeigt
WerkMate außerdem die Gesamtvorgabezeit in Minuten sowie in Stunden/Minuten:

> 48 Stück × 20 Minuten = 960,0 min (16 h 00 min)

Ist die Gesenknummer bereits im Katalog vorhanden, kann sie aus der Liste
gewählt werden. WerkMate bietet danach nur die zugehörigen Arbeitsgänge an und
trägt deren aktuelle Vorgabezeit automatisch ein.

### Noch schneller: Schnellstart

Im Reiter **Schnellstart** reichen folgende Kombinationen:

- Gesamtmenge und Stückzeit
- Gesamtmenge und Gesenknummer, wenn im Katalog genau ein Arbeitsgang hinterlegt ist
- Gesamtmenge, Gesenknummer und Arbeitsgang

Auftragsnummer und Notiz sind optional. Ohne Auftragsnummer erzeugt WerkMate
eine eindeutige Schnellauftragsnummer. Anmeldezeit und aktuelle Schicht sind
bereits vorausgefüllt. WerkMate legt den Auftrag an, bestimmt die innerhalb der
Restschicht vollständig mögliche Einsatzmenge und startet ihn sofort.

## 4. Gesenk- und Vorgabezeiten-Katalog pflegen

Öffne den Reiter **Gesenk-Katalog**. Für jede Kombination werden gespeichert:

- Gesenknummer und optionale Beschreibung
- Arbeitsgangcode, beispielsweise `FP1`
- optionale verständliche Arbeitsgangbezeichnung
- aktuelle Vorgabezeit pro Stück
- optionale Notiz zum Gesenk

Eine bereits vorhandene Kombination aus Gesenk und Arbeitsgang wird beim
erneuten Speichern aktualisiert. Neue Aufträge erhalten danach die neue
Vorgabezeit. Bereits gespeicherte Aufträge und historische Meldungen verändern
sich dadurch nicht.

Nicht mehr benötigte Vorgaben können deaktiviert werden. Sie verschwinden aus
der Auswahl, ohne historische Daten zu löschen.

Der **AG-Code** ist die kurze betriebliche Kennung wie `FP`, `FP1`, `ZP2` oder
`KR`. Er ist erforderlich, weil ein Gesenk mehrere Arbeitsgänge mit
unterschiedlichen Zeiten besitzen kann. Die ausgeschriebene Bezeichnung ist
optional. Bleibt sie leer, verwendet WerkMate automatisch den AG-Code als
Anzeigetext. Für einen einfachen Katalogeintrag genügen daher Gesenknummer,
AG-Code und Minuten pro Stück.

## 5. Einen Arbeitseinsatz starten

1. Markiere den gewünschten Auftrag in der Liste.
2. Gib bei **Menge** an, wie viele der offenen Stücke du jetzt bearbeiten willst.
3. Gib die gewünschte betriebliche Anmeldezeit ein. Das Format ist
   `JJJJ-MM-TT HH:MM`.
4. Wähle Schicht 1, 2 oder 3. Ohne Auswahl wird keine Pause und keine
   Reststückprognose bis Schichtende berechnet.
5. Klicke auf **Arbeit starten**.

Noch vor dem Start zeigt WerkMate automatisch die Sollleistung bis zum
Schichtende. Beispiel bei 20 Minuten pro Stück in der Frühschicht:

- produktiv verfügbare Zeit: 462 Minuten
- rechnerische Sollleistung: 23,1 Stück
- innerhalb der Schicht vollständig fertigstellbar: 23 Stück
- verbleibende Zeit im begonnenen nächsten Stück: 2 Minuten
- vollständiges 24. Stück: 18 Minuten Überzeit

Die Berechnung ändert sich sofort mit der Anmeldezeit. Bei einem teilweise
bearbeiteten Auftrag wird sie außerdem auf die tatsächlich offene Menge begrenzt.

WerkMate schlägt als **Einsatzmenge** nur die Stückzahl vor, die innerhalb der
Restschicht vollständig fertig werden kann. Ein Auftrag mit 48 offenen Stück
wird deshalb nicht als ein durchgehender 48-Stück-Einsatz gestartet. Im Beispiel
werden 23 Stück für diesen persönlichen Einsatz geplant; 25 bleiben anschließend
als Restauftrag offen.

WerkMate wechselt zum laufenden Auftrag und zeigt:

- Auftrags-, Gesenk- und Arbeitsgangnummer
- Menge und Vorgabezeit
- geplante Rückmeldezeit für die gewählte Einsatzmenge
- verbleibende Zeit beziehungsweise rote Überziehung
- laut Vorgabe vollständig mögliche Stücke bis Schichtende
- rechnerische Sollleistung mit einer Dezimalstelle
- Überzeit, die das nächste Stück verursachen würde

Die Schichtprognose wird ab der gewählten Anmeldezeit berechnet und bleibt
während des Einsatzes stabil. Nur der Countdown bis zur geplanten Rückmeldung
läuft weiter.

Die mögliche Überzeit wird in Klartext angezeigt. Statt einer abstrakten Angabe
wie `+00:05:00` steht dort beispielsweise:

> Ein weiteres Stück wäre um 21:50 fertig (5 Min. nach Schichtende).

Diese Information ist nur eine Entscheidungshilfe. Sie fordert nicht dazu auf,
das weitere Stück zu beginnen.

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

1. Trage bei **Tatsächlich bearbeitet** die wirklich fertiggestellte Menge ein.
2. Trage bei **Betrieblich rückgemeldet** die heute gemeldete Menge ein. Bleibt
   das Feld leer, verwendet WerkMate automatisch die bearbeitete Menge.
3. Trage die gewünschte Abmeldezeit ein oder klicke auf **Aktuelle Zeit**.
4. Ergänze bei Bedarf eine Meldungsnotiz.
5. Entscheide zwischen zwei Aktionen:

   - **Teilrückmelden / Arbeitseinsatz unterbrechen:** Nur die eingetragene
     Stückzahl wird gemeldet. Der übrige Auftrag bleibt offen.
   - **Gesamtauftrag vollständig beenden:** Alle noch offenen Stück werden als
     fertig gemeldet. Dafür ist eine zusätzliche Bestätigung erforderlich.

Die Abmeldezeit darf von der geplanten Rückmeldezeit abweichen. Liegt sie vor der
Anmeldezeit oder mehr als 30 Minuten von der geplanten Rückmeldezeit entfernt, zeigt WerkMate eine Warnung. Die
Eingabe kann trotzdem bewusst bestätigt werden.

Beispiel:

- ursprüngliche Menge: 24 Stück
- persönlich fertiggemeldet: 20 Stück
- anschließend offen: 4 Stück

Der Auftrag bleibt als teilweise erledigt gespeichert. Die vier offenen Stücke
können an einem späteren Tag erneut gestartet werden.

## 8. Guthaben erzeugen und später rückmelden

Guthaben entsteht, wenn mehr Stück tatsächlich bearbeitet als am selben Tag
betrieblich rückgemeldet werden.

Beispiel für Auftrag 4261:

- Gesamtmenge: 40 Stück
- tatsächlich bearbeitet: 40/40
- heute betrieblich rückgemeldet: 18/40
- Guthaben: 22 Stück
- Vorgabe: 15 Minuten/Stück
- Guthabenwert: 330 Minuten beziehungsweise 5 h 30 min
- noch tatsächlich zu bearbeiten: 0 Stück

### Guthaben nach Stückzahl anmelden

1. Auftrag in der Auftragsliste markieren.
2. **Guthaben anmelden** wählen.
3. **Nach Stückzahl** aktivieren und beispielsweise 10 eingeben.
4. Anmeldezeit und Schicht prüfen.
5. Guthabeneinsatz starten und zur angezeigten Zeit rückmelden.

Die 10 Stück belegen 150 Minuten produktive Schichtzeit. Danach bleiben im
Beispiel 12 Guthabenstücke erhalten.

### Guthaben nach exakter Zeit anmelden

Wenn der Vorgesetzte beispielsweise zwei Stunden vorgibt:

1. **Nach exakter Zeit in Minuten** wählen.
2. `120` Minuten eingeben.
3. WerkMate zeigt die rechnerische Dezimalstückzahl und einen normal gerundeten
   Vorschlag.
4. Beim Abmelden entscheidest du selbst über die tatsächlich einzutragende ganze
   Stückzahl.

Bei 17 min/Stück entsprechen 120 Minuten rechnerisch 7,06 Stück; WerkMate
schlägt 7 vor. Du kannst beim Abmelden trotzdem 7 oder 8 eingeben. Die gewählten
120 Minuten bestimmen exakt den Startzeitpunkt des nächsten Auftrags. Das
verbleibende Guthaben berechnet sich anschließend aus deiner eingegebenen
Stückzahl. Guthaben kann beliebig über mehrere Tage verteilt werden.

## 9. Mehrere Aufträge zu einem Schichtplan verbinden

Im Reiter **Schichtplan** können Arbeits- und Guthabenblöcke in einer festen
Reihenfolge kombiniert werden. Mit **SCHICHT BERECHNEN** wird der Plan zugleich
lokal gespeichert und beim nächsten Programmstart automatisch wieder geladen.
Für jeden Planpunkt stehen vier Arten bereit:

**Manuellen Auftrag eintragen** nimmt zusätzlich Arbeiten auf, die weder im
Gesenk-Katalog noch unter Aufträge vorhanden sind. Diese können nur für den
aktuellen Schichtablauf gelten oder optional dauerhaft als Auftrag gespeichert
werden. Über **Startzeit bearbeiten** kann ein Planpunkt eine feste eigene
Startzeit erhalten; ohne Vorgabe schließt er automatisch an den vorherigen an.

- **Offene Stück fest:** Eine vorgegebene Restmenge vollständig einplanen.
- **Restschicht mit Auftrag füllen:** So viele vollständige Stück berechnen, wie
  nach den vorherigen Planpunkten noch möglich sind.
- **Guthaben nach Stück:** Eine bestimmte Guthabenmenge zuerst rückmelden.
- **Guthaben nach Minuten:** Eine exakt vorgegebene Guthabenzeit reservieren.

Beispiel:

1. 8720 mit 12 offenen Stück als feste Menge hinzufügen.
2. 4261 mit 40 Stück und 15 min/Stück als **Restschicht füllen** hinzufügen.
3. Schicht 1 und Start 05:45 wählen.
4. **Schicht berechnen** anklicken.

WerkMate berücksichtigt die feste Pause nur einmal im fortlaufenden Zeitplan und
zeigt für jeden Auftrag Start, Ende, ganze Stück, rechnerische Dezimalstückzahl
und mögliche Überzeit. Im Beispiel mit 20 min/Stück für 8720 ergibt sich:

- 8720: 12 Stück, 05:45–10:03 inklusive Pause
- 4261: verbleibende 222 produktive Minuten, rechnerisch 14,8 Stück
- 4261: 14 Stück vollständig, geplantes Ende 13:33

Mit **Ersten Planpunkt starten** wird der erste Block übernommen. Nach seiner
Rückmeldung verwendet WerkMate die tatsächliche Abmeldezeit automatisch als
Beginn des Restplans. Alle folgenden Startzeiten, Stückzahlen und Überzeiten
werden neu berechnet. Der Restplan bleibt auch nach dem Schließen erhalten.

Der berechnete Ablauf erscheint als verbundene Kartenfolge. Jede Karte zeigt
Auftrag, Gesenk/AG, Start, Ende, Stückzahl und Dauer. Oberhalb stehen sowohl die
gesamte Uhrzeit des Ablaufs als auch die reine produktive Vorgabezeit.

Die Reihenfolge kann in der Liste über **▲/▼** oder durch Ziehen eines Eintrags
mit der Maus geändert werden. Auch während der erste Auftrag bereits läuft,
können zukünftige Planpunkte ergänzt, entfernt oder umsortiert und erneut
gespeichert werden. Der aktive Auftrag selbst bleibt dabei unverändert.

## 10. Einen versehentlich gestarteten Einsatz abbrechen

Klicke beim laufenden Auftrag auf **Fehlstart / Arbeitseinsatz abbrechen**. Es
werden keine Stück gemeldet und der Auftrag bleibt vollständig offen. Danach
kannst du ihn mit korrigierter Menge, Zeit oder Schicht neu starten.

Der abgebrochene Einsatz bleibt mit Status `abgebrochen` in der Historie, damit
keine Daten unbemerkt verschwinden.

## 11. Einen Restauftrag später fortsetzen

1. Öffne den Reiter **Aufträge**.
2. Markiere den teilweise erledigten Auftrag.
3. Trage die gewünschte Einsatzmenge ein – höchstens die offene Menge.
4. Trage die neue Anmeldezeit und Schicht ein.
5. Klicke auf **Arbeit starten**.

Jeder Arbeitseinsatz wird separat gespeichert. Dadurch bleiben verschiedene
Tage und Teilrückmeldungen nachvollziehbar.

## 12. Historie ansehen

Der Reiter **Historie** zeigt alle persönlichen Arbeitseinsätze mit:

- Datum
- Auftrag, Gesenk und Arbeitsgang
- gemeldeter An- und Abmeldezeit
- fertiggemeldeter Stückzahl
- geplanter und tatsächlich gemeldeter Stückzahl
- Zeitabweichung in Minuten und Prozent
- Stückabweichung als Anzahl und Prozent
- Status

Ein Doppelklick auf einen Eintrag öffnet weitere Details einschließlich
geplanter Rückmeldezeit und Notiz.

Die Suche findet Auftragsnummern, Gesenknummern, Arbeitsgänge und Notiztexte.
Zusätzlich kann die Liste nach Meldungsstatus gefiltert werden.

### Bedeutung der Leistungsfarben

Die Auswertung bezieht sich immer auf den einzelnen geplanten Arbeitseinsatz:

- 🔴 **Verzug:** Abmeldung erfolgte nach der geplanten Rückmeldezeit.
- 🟢 **Früher:** Abmeldung erfolgte vor der geplanten Rückmeldezeit.
- 🟢 **Mehr Stück:** Mehr Stück gemeldet als für den Einsatz geplant.
- 🔴 **Weniger Stück:** Weniger Stück gemeldet als für den Einsatz geplant.

Zeit- und Stückergebnis werden bewusst getrennt bewertet. Wer früher abmeldet,
aber gleichzeitig weniger Stück meldet, erhält deshalb eine grüne Zeitangabe und
eine rote Stückangabe. Abgebrochene und noch laufende Einsätze werden nicht
bewertet.

Der Zeitprozentsatz verwendet die Vorgabezeit der geplanten Einsatzmenge als
Basis. Der Stückprozentsatz verwendet die geplante Stückzahl als Basis.

Der Reiter **Auswertung** fasst dieselben Daten wahlweise für heute oder die
laufende Woche zusammen. Angezeigt werden Einsätze, bearbeitete und gemeldete
Stück, Guthabenänderung sowie die zusammengefasste Zeit- und Stückabweichung.
Darunter stehen die einzelnen Tageswerte. Grün bedeutet früher beziehungsweise
mehr als geplant, Rot bedeutet später beziehungsweise weniger als geplant.

## 13. Gespeicherte Aufträge korrigieren

Markiere einen Auftrag und klicke auf **Auftrag bearbeiten** oder doppelklicke
auf seine Tabellenzeile. Gesenknummer, Arbeitsgang, Gesamtmenge, aktuelle
Vorgabezeit und Auftragsnotiz können geändert werden.

Historische Arbeitseinsätze behalten ihre damals gespeicherte Vorgabezeit. Über
**Änderungen anzeigen** bleibt nachvollziehbar, wann welcher Auftragswert
korrigiert wurde.

Abgeschlossene Rückmeldungen können im Reiter **Historie** ausgewählt und über
**Rückmeldung korrigieren** berichtigt werden. Änderbar sind Anmeldezeit,
Abmeldezeit, tatsächlich bearbeitete Stück, betrieblich rückgemeldete Stück und
Notiz. Ein Korrekturgrund ist verpflichtend. **Korrekturprotokoll** zeigt jeden
alten und neuen Wert samt Zeitpunkt und Begründung. Offene Menge, Guthaben und
Leistungsabweichungen werden automatisch neu berechnet.

Mit **Duplizieren** entsteht eine unabhängige Kopie des ausgewählten Auftrags;
direkt danach öffnet sich der Bearbeitungsdialog für Auftragsnummer, Gesenk, AG,
Menge, Stückzeit und Notiz. **In Papierkorb** blendet einen Auftrag aus den
normalen Listen aus. Im **Papierkorb** kann er wiederhergestellt oder mitsamt
seinen Rückmeldungen endgültig gelöscht werden.

Über **Auftragsdaten ergänzen** in der Historie können auch automatisch erzeugte
Schnellstart-Auftragsnummern und fehlende Gesenk-/AG-Daten später berichtigt
werden. Eine fehlerhafte Rückmeldung wird über **Stornieren** aus Mengen,
Guthaben und Auswertungen entfernt. Der **Storno-Papierkorb** erlaubt
Wiederherstellen oder endgültiges Bereinigen.

Ein abgegebener Restauftrag kann markiert und mit **Abgegebenen Auftrag wieder
aufnehmen** erneut in die persönliche Bearbeitung übernommen werden.

## 14. Wo liegen die Daten?

Die lokale Datenbank liegt standardmäßig hier:

```text
%LOCALAPPDATA%\WerkMate\werkmate.sqlite3
```

Unter einem typischen Windows-Benutzerkonto entspricht das ungefähr:

```text
C:\Users\DEIN-NAME\AppData\Local\WerkMate\werkmate.sqlite3
```

Die Daten werden nicht automatisch zu GitHub oder in eine Cloud übertragen.

## 15. Datensicherung

Klicke oben rechts auf **Daten sichern**, wähle einen Zielordner und speichere
die vorgeschlagene `.sqlite3`-Datei. WerkMate erzeugt eine konsistente Kopie
der gesamten lokalen Historie.

Alternativ ist eine manuelle Sicherung möglich:

1. WerkMate vollständig schließen.
2. Die Datei `werkmate.sqlite3` aus dem oben genannten Ordner kopieren.
3. Die Kopie an einem sicheren Ort ablegen.

Alternativ kann die Datei bei geschlossenem WerkMate weiterhin manuell an
denselben Ort zurückkopiert werden.

Im Reiter **Einstellungen** kann eine Sicherung inzwischen direkt über
**Sicherung wiederherstellen** ausgewählt werden. WerkMate prüft zuerst, ob es
sich um eine intakte WerkMate-Datenbank handelt, und legt vor dem Ersetzen
automatisch eine zusätzliche Kopie des aktuellen Stands an.

**CSV-Dateien exportieren** erzeugt im gewählten Ordner zwei Excel-taugliche,
mit Semikolon getrennte Dateien: eine Auftragsübersicht und eine vollständige
Rückmeldungshistorie.

## 16. Schichten und Pausen einstellen

Im Reiter **Einstellungen** stehen die drei Schichten jeweils in einer eigenen
Zeile. Beginn, Ende, Pausenbeginn und Pausenende werden im Format `HH:MM`
eingetragen. Nachtschichten über Mitternacht erkennt WerkMate automatisch.

Die Pause muss vollständig innerhalb der jeweiligen Schicht liegen. Sie stoppt
nicht die sichtbare Uhr, sondern wird ausschließlich aus der produktiven Sollzeit
herausgerechnet. Änderungen gelten für neue Einsätze und neue Berechnungen;
bereits gespeicherte Rückmeldungen werden nicht nachträglich verändert.

**Standardzeiten einsetzen** trägt die ursprünglichen WerkMate-Zeiten wieder in
das Formular ein. Dauerhaft übernommen werden sie erst mit
**EINSTELLUNGEN SPEICHERN**.

## 17. Bekannte Grenzen dieses Stands

- noch keine Android- oder iOS-App
- keine zuverlässige Benachrichtigung bei geschlossenem Programm

Der Rechenkern, die lokale Speicherung und der grundlegende persönliche Ablauf
sind bereits vorhanden und automatisiert getestet.

## 18. Optionale Konsolenbedienung

Die bisherige Konsolenoberfläche bleibt erhalten. Ihre Befehle sind in
[`KONSOLEN-MVP.md`](KONSOLEN-MVP.md) dokumentiert.
