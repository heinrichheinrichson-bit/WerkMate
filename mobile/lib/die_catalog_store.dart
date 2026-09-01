import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'card_scan.dart';

class DieCatalogEntry {
  const DieCatalogEntry({
    required this.id,
    required this.dieNumber,
    required this.operation,
    required this.minutesPerPiece,
    this.note = '',
  });

  final String id;
  final String dieNumber;
  final String operation;
  final double minutesPerPiece;
  final String note;

  String get normalizedDieNumber => normalizeDieNumber(dieNumber) ?? dieNumber;
  String get normalizedOperation => operation.trim().toUpperCase();
  String get key => '$normalizedDieNumber|$normalizedOperation';

  Map<String, Object?> toJson() => {
    'id': id,
    'dieNumber': normalizedDieNumber,
    'operation': normalizedOperation,
    'minutesPerPiece': minutesPerPiece,
    'note': note,
  };

  factory DieCatalogEntry.fromJson(Map<String, dynamic> json) =>
      DieCatalogEntry(
        id: json['id'] as String,
        dieNumber: json['dieNumber'] as String,
        operation: json['operation'] as String,
        minutesPerPiece: (json['minutesPerPiece'] as num).toDouble(),
        note: json['note'] as String? ?? '',
      );
}

class DieCatalogStore {
  static const _key = 'die_catalog_v1';

  Future<List<DieCatalogEntry>> load() async {
    final raw = (await SharedPreferences.getInstance()).getString(_key);
    if (raw == null) return [];
    try {
      final entries = (jsonDecode(raw) as List)
          .map(
            (value) => DieCatalogEntry.fromJson(
              Map<String, dynamic>.from(value as Map),
            ),
          )
          .toList();
      entries.sort((a, b) => a.key.compareTo(b.key));
      return entries;
    } catch (_) {
      return [];
    }
  }

  Future<void> write(List<DieCatalogEntry> entries) async {
    await (await SharedPreferences.getInstance()).setString(
      _key,
      jsonEncode(entries.map((entry) => entry.toJson()).toList()),
    );
  }
}
