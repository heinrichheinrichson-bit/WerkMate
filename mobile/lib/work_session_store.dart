import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'domain.dart';

class WorkSessionSnapshot {
  const WorkSessionSnapshot({
    required this.steps,
    required this.index,
    this.startedAt,
    this.targetEnd,
  });

  final List<ScheduleStep> steps;
  final int index;
  final DateTime? startedAt, targetEnd;
  bool get isRunning => startedAt != null && targetEnd != null;

  Map<String, Object?> toJson() => {
    'steps': steps.map((step) => step.toJson()).toList(),
    'index': index,
    'startedAt': startedAt?.toIso8601String(),
    'targetEnd': targetEnd?.toIso8601String(),
  };

  factory WorkSessionSnapshot.fromJson(Map<String, dynamic> json) =>
      WorkSessionSnapshot(
        steps: (json['steps'] as List)
            .map(
              (step) =>
                  ScheduleStep.fromJson(Map<String, dynamic>.from(step as Map)),
            )
            .toList(),
        index: json['index'] as int,
        startedAt: json['startedAt'] == null
            ? null
            : DateTime.parse(json['startedAt'] as String),
        targetEnd: json['targetEnd'] == null
            ? null
            : DateTime.parse(json['targetEnd'] as String),
      );
}

class WorkSessionStore {
  static const _key = 'active_work_session_v1';

  Future<WorkSessionSnapshot?> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return null;
    try {
      return WorkSessionSnapshot.fromJson(
        Map<String, dynamic>.from(jsonDecode(raw) as Map),
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> save(WorkSessionSnapshot snapshot) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(snapshot.toJson()));
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}
