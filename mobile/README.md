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
