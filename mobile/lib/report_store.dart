import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'domain.dart';

DateTime minutePrecision(DateTime value) =>
    DateTime(value.year, value.month, value.day, value.hour, value.minute);

String? validateReportTime({
  required DateTime now,
  required DateTime startedAt,
  required DateTime reportedAt,
}) {
  final current = minutePrecision(now);
  final start = minutePrecision(startedAt);
  final report = minutePrecision(reportedAt);
  if (report.isAfter(current)) {
    return 'Rückmeldungen in der Zukunft sind nicht erlaubt.';
  }
  if (report.isBefore(current.subtract(const Duration(minutes: 59)))) {
    return 'Die Rückmeldezeit darf höchstens 59 Minuten zurückliegen.';
  }
  if (report.isBefore(start)) {
    return 'Die Abmeldezeit darf nicht vor der Startzeit liegen.';
  }
  return null;
}

class WorkReport {
  const WorkReport({
    required this.id,
    required this.item,
    required this.plannedPieces,
    required this.actualPieces,
    required this.reportedPieces,
    required this.startedAt,
    required this.endedAt,
    required this.plannedEnd,
    required this.completedOrder,
    required this.note,
  });

  final String id;
  final WorkItem item;
  final int plannedPieces, actualPieces, reportedPieces;
  final DateTime startedAt, endedAt, plannedEnd;
  final bool completedOrder;
  final String note;

  double get actualMinutes => endedAt.difference(startedAt).inSeconds / 60;
  double get plannedMinutes => plannedEnd.difference(startedAt).inSeconds / 60;
  double get timeDeviationMinutes => actualMinutes - plannedMinutes;
  int get pieceDeviation => actualPieces - plannedPieces;

  Map<String, Object> toJson() => {
    'id': id,
    'item': item.toJson(),
    'plannedPieces': plannedPieces,
    'actualPieces': actualPieces,
    'reportedPieces': reportedPieces,
    'startedAt': startedAt.toIso8601String(),
    'endedAt': endedAt.toIso8601String(),
    'plannedEnd': plannedEnd.toIso8601String(),
    'completedOrder': completedOrder,
    'note': note,
  };

  factory WorkReport.fromJson(Map<String, dynamic> json) => WorkReport(
    id: json['id'] as String,
    item: WorkItem.fromJson(Map<String, dynamic>.from(json['item'] as Map)),
    plannedPieces: json['plannedPieces'] as int,
    actualPieces: json['actualPieces'] as int,
    reportedPieces: json['reportedPieces'] as int,
    startedAt: DateTime.parse(json['startedAt'] as String),
    endedAt: DateTime.parse(json['endedAt'] as String),
    plannedEnd: DateTime.parse(json['plannedEnd'] as String),
    completedOrder: json['completedOrder'] as bool,
    note: json['note'] as String? ?? '',
  );
}

class ReportStore {
  static const _key = 'work_reports_v1';

  Future<List<WorkReport>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return [];
    try {
      return (jsonDecode(raw) as List)
          .map(
            (value) =>
                WorkReport.fromJson(Map<String, dynamic>.from(value as Map)),
          )
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> append(WorkReport report) async {
    final reports = await load()
      ..add(report);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode(reports.map((value) => value.toJson()).toList()),
    );
  }
}
