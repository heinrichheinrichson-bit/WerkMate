import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'domain.dart';

class PlanStore {
  static const _key = 'simple_mobile_plans_v1';

  Future<List<ShiftPlan>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) return [];
    try {
      return (jsonDecode(raw) as List)
          .map(
            (item) =>
                ShiftPlan.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> write(List<ShiftPlan> plans) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode(plans.map((p) => p.toJson()).toList()),
    );
  }
}
