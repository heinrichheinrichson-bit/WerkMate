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
