import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class AlarmService {
  AlarmService._();
  static final instance = AlarmService._();
  static const notificationId = 8720;
  final plugin = FlutterLocalNotificationsPlugin();
  bool initialized = false;

  Future<void> initialize() async {
    if (initialized) return;
    tz.initializeTimeZones();
    await plugin.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
    );
    initialized = true;
  }

  Future<void> requestPermissions() async {
    await initialize();
    if (!kIsWeb && Platform.isAndroid) {
      final android = plugin
          .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin
          >();
      await android?.requestNotificationsPermission();
      await android?.requestExactAlarmsPermission();
      await android?.requestFullScreenIntentPermission();
    } else if (!kIsWeb && Platform.isIOS) {
      await plugin
          .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin
          >()
          ?.requestPermissions(alert: true, badge: true, sound: true);
    }
  }

  Future<void> schedule(DateTime target, String workName) async {
    await initialize();
    await cancel();
    final scheduled = tz.TZDateTime.from(target, tz.local);
    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        'work_target_alarm_v2',
        'WerkMate Arbeitsalarm',
        channelDescription:
            'Erinnert an die Rückmeldung oder Verlängerung einer Arbeit.',
        importance: Importance.max,
        priority: Priority.high,
        playSound: true,
        enableVibration: true,
        category: AndroidNotificationCategory.alarm,
        ongoing: true,
        autoCancel: false,
        fullScreenIntent: true,
        additionalFlags: Int32List.fromList([4]), // FLAG_INSISTENT
      ),
      iOS: const DarwinNotificationDetails(
        presentAlert: true,
        presentSound: true,
      ),
    );
    try {
      await plugin.zonedSchedule(
        notificationId,
        'Sollzeit erreicht',
        '$workName rückmelden oder neue Endzeit setzen.',
        scheduled,
        details,
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      );
    } catch (_) {
      await plugin.zonedSchedule(
        notificationId,
        'Sollzeit erreicht',
        '$workName rückmelden oder neue Endzeit setzen.',
        scheduled,
        details,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    }
  }

  Future<void> cancel() async {
    await initialize();
    await plugin.cancel(notificationId);
  }
}
