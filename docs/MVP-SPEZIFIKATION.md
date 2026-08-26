# WerkMate – verbindliche MVP-Spezifikation

Stand: 26. August 2026  
Spezifikationsversion: 1.0

## 1. Ziel

WerkMate unterstützt genau eine arbeitende Person bei der zeitlichen Planung
und persönlichen Dokumentation ihrer Aufträge. Die App ersetzt keine
betriebliche Software. Alle Daten werden ausschließlich lokal gespeichert.

## 2. Begriffe

- **Auftrag:** Betrieblicher Auftrag mit Auftragsnummer, Gesenknummer,
  Arbeitsgang und ursprünglicher Menge.
- **Arbeitseinsatz:** Eine persönliche Bearbeitungsphase an einem Auftrag.
  Ein Auftrag kann an mehreren Tagen mehrere Arbeitseinsätze haben.
- **Teilrückmeldung:** Abschluss eines Arbeitseinsatzes mit persönlich
  fertiggemeldeter Stückzahl und gewählter Abmeldezeit.
- **Restauftrag:** Noch offene Menge eines teilweise bearbeiteten Auftrags.
- **Tatsächlicher Zeitpunkt:** Zeitpunkt einer Bedienhandlung in WerkMate.
- **Gemeldeter Zeitpunkt:** Vom Benutzer gewählte An- oder Abmeldezeit. Diese
  darf rückwirkend oder abweichend sein.

## 3. Vorgabezeit

Die Vorgabezeit ist die vom Betrieb vorgegebene Zeit, in der der Auftrag
fertiggestellt werden soll. Sie ist keine Messung der tatsächlichen Leistung.

`Gesamtvorgabezeit = Menge × Vorgabezeit je Stück`

Dezimalwerte wie `7,5 Minuten` sind erlaubt. Intern rechnet WerkMate in ganzen
Sekunden, um Rundungsfehler zu vermeiden.

## 4. Schichten

Voreinstellungen:

| Schicht | Beginn | Ende Folgetag | Pause |
|---|---:|---:|---:|
| 1 | 05:45 | 13:45 | 08:45–09:03 |
| 2 | 13:45 | 21:45 | 17:45–18:03 |
| 3 | 21:45 | 05:45 | 01:45–02:03 |

Beginn und Ende können für Sonderfälle und Überstunden geändert werden.
Nachtschichten werden als konkrete Zeiträume mit Datum behandelt.

## 5. Pausenabrechnung

Der Countdown wird nicht manuell pausiert. Die feste Pause ist ausschließlich
eine Abrechnungsregel. Überschneidet sich die rechnerische Bearbeitung mit dem
Pausenfenster, zählt die überschnittene Pausenzeit nicht als produktive
Vorgabezeit und verschiebt das Soll-Ende entsprechend.

- keine Überschneidung: kein Zuschlag
- vollständige Überschneidung: 18 Minuten Zuschlag
- teilweise Überschneidung: nur die tatsächliche zeitliche Überschneidung

Wann die Person tatsächlich Pause macht, wird im MVP nicht erfasst.

## 6. Laufender Arbeitseinsatz

Beim Start speichert WerkMate sowohl den tatsächlichen Bedienzeitpunkt als auch
die frei gewählte Anmeldezeit. Das Soll-Ende basiert auf der gemeldeten
Anmeldezeit, Vorgabezeit und festen Pausenabrechnung.

Der Countdown wird stets aus `Soll-Ende − aktuelle Zeit` berechnet. Nach Ablauf
der Sollzeit läuft er als deutlich erkennbare Überziehung weiter. Das
Soll-Ende löst eine lokale Benachrichtigung aus; der Auftrag endet nicht
automatisch.

Stückzahlen während der Laufzeit sind ausdrücklich Prognosen laut Vorgabe und
keine Behauptung über tatsächlich fertiggestellte Stücke.

## 7. Teilrückmeldung

Beim bewussten Beenden gibt der Benutzer die persönlich fertiggestellte Menge
ein. Er kann als Abmeldezeit wählen:

- aktuellen Zeitpunkt,
- berechnetes Soll-Ende,
- beliebige eigene Zeit.

Jede Zeit ist zulässig. Auffällige Werte erzeugen eine Warnung mit bewusster
Bestätigung, aber kein hartes Verbot. Der tatsächliche Bestätigungszeitpunkt
bleibt zusätzlich gespeichert.

Die gewählte Abmeldezeit wird als vorgeschlagene Anmeldezeit des nächsten
Auftrags verwendet. Ein rückwirkend gestarteter Auftrag kann daher beim
Öffnen bereits laufende Sollzeit besitzen.

## 8. Restauftrag

`offene Menge = ursprüngliche Menge − Summe eigener Teilrückmeldungen`

Nach einer Teilrückmeldung bleibt der Auftrag teilweise offen. Der Benutzer
kann ihn später erneut aufnehmen oder als **abgegeben/nicht weiterverfolgt**
markieren. Dieser Status bedeutet nicht, dass der betriebliche Auftrag erledigt
ist; lediglich die persönliche Nachverfolgung endet.

## 9. Notizen

- Auftragsnotiz: gilt für den gesamten Auftrag.
- Meldungsnotiz: gehört zu einem konkreten Arbeitseinsatz bzw. einer
  Teilrückmeldung.

## 10. Historie und Korrekturen

Die Historie speichert mindestens:

- Datum und Schicht
- Auftragsnummer, Gesenknummer und Arbeitsgang
- ursprüngliche, persönlich gemeldete und offene Menge
- damals gültige Vorgabezeit
- tatsächliche und gemeldete Anmeldezeit
- Soll-Ende
- tatsächlichen Bestätigungszeitpunkt und gemeldete Abmeldezeit
- verrechnete Pause und zeitliche Abweichung
- Notizen und Status

Spätere Korrekturen überschreiben die fachliche Ansicht, werden aber in einem
Änderungsprotokoll mit altem Wert, neuem Wert und Änderungszeitpunkt erhalten.

## 11. Nicht Bestandteil des ersten MVP

- zentrale Vorgesetztenansicht und mehrere Arbeitnehmer
- Cloud-Synchronisierung oder Benutzerkonten
- betriebliche Rückmeldung an Fremdsysteme
- Statistiken und PDF-Berichte
- vollständiger Gesenk- und Vorgabezeiten-Katalog
- automatische Erfassung tatsächlicher Pausen oder fertiger Einzelstücke

## 12. Datenschutz und Sicherung

Die operative Datenbank liegt nur lokal. Ein späterer manueller Export und eine
lokale Sicherungs-/Wiederherstellungsfunktion sind vorgesehen, da ein verlorenes
Gerät sonst auch die persönliche Historie verliert.

