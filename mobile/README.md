# WerkMate Mobile 0.19.0

Erster getrennter Flutter-Prototyp für Android und später iOS.

Bereits enthalten:

- Schnellstart mit Menge und Stückzeit
- optionale Auftrags- und Gesenknummer
- Schichtprognose mit festen Pausen
- laufender Einsatz mit geplanter Rückmeldezeit
- getrennte Eingabe für bearbeitete und betrieblich gemeldete Stück
- einfache mobile Historie und Guthabenänderung

Dieser frühe Prototyp speichert seine Daten noch nicht dauerhaft und übernimmt
noch nicht den Katalog oder die Datenbank der PC-App. Er dient zunächst dazu,
Bedienung und mobile Darstellung zu testen.

## Prüfen und starten

```powershell
cd mobile
flutter analyze
flutter test
flutter run
```

## APK bauen

```powershell
flutter build apk --release
```

Die APK liegt anschließend unter
`mobile\build\app\outputs\flutter-apk\app-release.apk`.
