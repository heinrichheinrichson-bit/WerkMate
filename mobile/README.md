# WerkMate Mobile

Smartphone-first-Neustart von WerkMate. Die Python-/Tkinter-Anwendung bleibt
als geprüfte fachliche Referenz erhalten.

Aktueller Umfang:

- Navigation `Heute`, `Planen`, `Pläne`, `Mehr`
- mehrere Arbeiten als touchfreundliche Karten
- Reihenfolge per langem Ziehen
- feste Schichtpausen und Soll-Zeitberechnung
- lokale Planspeicherung
- manueller Arbeitsstart, Countdown, Überzeit und erneute Alarmzeit
- kein automatischer Start der nächsten Arbeit
- responsive Anordnung für Hochformat, Querformat und Tablets
- laufender Arbeitsmodus wird nach einem App-Neustart wiederhergestellt
- anhaltender Android-Arbeitsalarm am Soll-Ende, auch im Hintergrund
- Alarm wird erst durch Rückmeldung, Verlängerung oder Stummschalten beendet
- getrennte Auftragsnummer, Gesenknummer und Arbeitsgang je Arbeit
- ganze Überstunden per Minus/Plus mit sofortiger Neuplanung
- Android-Weckton statt des gewöhnlichen Benachrichtigungstons
- Schichtbelegung mit Kapazität, verplanten und noch offenen Minuten
- wählbare Auf-/Abrundung mit beiden Endzeiten und einer Empfehlung
- Restauftragsvolumen getrennt von der heutigen Schichtplanung
- vollständiger Tagesablauf mit Status und voraussichtlichen Folgezeiten unter `Heute`
- Sicherheitsabfragen vor Beenden, Zeitänderung oder Ersetzen eines aktiven Tages
- Planentwürfe bleiben vollständig vom laufenden Arbeitstag getrennt
- geschützte Rückmeldung mit tatsächlich bearbeiteten und betrieblich gemeldeten Stück
- frei korrigierbare Abmeldezeit, Teil-/Gesamtabschluss und optionale Notiz
- Rückmeldungen werden lokal für die spätere Historie gespeichert
- Rückmeldezeit ausschließlich von jetzt bis maximal 59 Minuten zurück
- Schnellwahl für aktuelle Uhrzeit oder zulässige Planzeit
- Folgeaufträge werden lückenlos ab der betrieblichen Rückmeldezeit neu geplant
- fünf Minuten Snooze bei erreichtem Soll-Ende; die Arbeit läuft dabei weiter
- Folgeaufträge im laufenden Tagesplan sicher umordnen
- neue Folgeaufträge während der Schicht anhängen und zeitlich neu berechnen
- mobile Rückmeldungshistorie mit Zeit- und Stückabweichungen
- Verzug und Minderstück rot, frühere Fertigstellung und Mehrstück grün
- einzelne Rückmeldungen nach Sicherheitsabfrage löschen
- lokal gespeicherter System-, Hell- oder Dunkelmodus
- kontrastreicher Countdown mit Restminuten, Prozent und Zeitfortschritt
- Guthaben automatisch aus bearbeiteten minus gemeldeten Stück berechnen
- Guthaben nach Auftrag, Gesenk und Arbeitsgang gebündelt anzeigen
- Guthaben nach Stück oder Minuten teilweise in neue Planungen übernehmen

Als nächste getrennte Bereiche sind die Historie sowie Einstellungen für
System-, Hell- und Dunkelmodus vorgesehen.

## Prüfen und starten

```powershell
cd mobile
flutter analyze
flutter test
flutter run
```

## Android-APK bauen

```powershell
flutter build apk --release
```
