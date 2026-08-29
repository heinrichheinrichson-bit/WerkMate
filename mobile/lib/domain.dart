import 'dart:math' as math;

class ShiftTemplate {
  const ShiftTemplate(
    this.number,
    this.name,
    this.startHour,
    this.startMinute,
    this.endHour,
    this.endMinute,
    this.pauseHour,
    this.pauseMinute,
    this.pauseEndHour,
    this.pauseEndMinute,
  );

  final int number;
  final String name;
  final int startHour, startMinute, endHour, endMinute;
  final int pauseHour, pauseMinute, pauseEndHour, pauseEndMinute;

  static const all = [
    ShiftTemplate(1, 'Frühschicht', 5, 45, 13, 45, 8, 45, 9, 3),
    ShiftTemplate(2, 'Spätschicht', 13, 45, 21, 45, 17, 45, 18, 3),
    ShiftTemplate(3, 'Nachtschicht', 21, 45, 5, 45, 1, 45, 2, 3),
  ];

  ShiftWindow onDate(
    DateTime day, {
    int? customStartMinutes,
    int overtimeHours = 0,
  }) {
    DateTime at(int hour, int minute, [int addDays = 0]) =>
        DateTime(day.year, day.month, day.day + addDays, hour, minute);
    final overnight = endHour * 60 + endMinute <= startHour * 60 + startMinute;
    final shiftStart = at(startHour, startMinute);
    final start = customStartMinutes == null
        ? shiftStart
        : at(customStartMinutes ~/ 60, customStartMinutes % 60);
    final end = at(
      endHour,
      endMinute,
      overnight ? 1 : 0,
    ).add(Duration(hours: overtimeHours));
    final pauseNextDay =
        overnight &&
        pauseHour * 60 + pauseMinute < startHour * 60 + startMinute;
    final pauseStart = at(pauseHour, pauseMinute, pauseNextDay ? 1 : 0);
    final pauseEnd = at(pauseEndHour, pauseEndMinute, pauseNextDay ? 1 : 0);
    return ShiftWindow(start, end, pauseStart, pauseEnd);
  }
}

class ShiftWindow {
  const ShiftWindow(this.start, this.end, this.pauseStart, this.pauseEnd);
  final DateTime start, end, pauseStart, pauseEnd;
}

enum RoundingChoice { automatic, down, up }

class WorkItem {
  const WorkItem({
    required this.id,
    required this.dieNumber,
    this.orderNumber = '',
    this.operation = '',
    this.roundingChoice = RoundingChoice.automatic,
    required this.quantity,
    required this.minutesPerPiece,
  });
  final String id, orderNumber, dieNumber, operation;
  final RoundingChoice roundingChoice;
  final int quantity;
  final double minutesPerPiece;

  String get name {
    final details = [
      if (orderNumber.trim().isNotEmpty) 'Auftrag ${orderNumber.trim()}',
      if (dieNumber.trim().isNotEmpty) 'Ges. ${dieNumber.trim()}',
      if (operation.trim().isNotEmpty) operation.trim().toUpperCase(),
    ];
    return details.isEmpty ? 'Manuelle Arbeit' : details.join(' · ');
  }

  Map<String, Object> toJson() => {
    'id': id,
    'orderNumber': orderNumber,
    'dieNumber': dieNumber,
    'operation': operation,
    'roundingChoice': roundingChoice.name,
    'quantity': quantity,
    'minutesPerPiece': minutesPerPiece,
  };

  factory WorkItem.fromJson(Map<String, dynamic> json) => WorkItem(
    id: json['id'] as String,
    orderNumber: json['orderNumber'] as String? ?? '',
    dieNumber: json['dieNumber'] as String? ?? json['name'] as String? ?? '',
    operation: json['operation'] as String? ?? '',
    roundingChoice: RoundingChoice.values.firstWhere(
      (value) => value.name == json['roundingChoice'],
      orElse: () => RoundingChoice.automatic,
    ),
    quantity: json['quantity'] as int,
    minutesPerPiece: (json['minutesPerPiece'] as num).toDouble(),
  );

  WorkItem copyWith({RoundingChoice? roundingChoice}) => WorkItem(
    id: id,
    orderNumber: orderNumber,
    dieNumber: dieNumber,
    operation: operation,
    roundingChoice: roundingChoice ?? this.roundingChoice,
    quantity: quantity,
    minutesPerPiece: minutesPerPiece,
  );
}

class ScheduleStep {
  const ScheduleStep({
    required this.item,
    required this.start,
    required this.end,
    required this.pauseStart,
    required this.pauseEnd,
    required this.capacityEnd,
    required this.wholePieces,
    required this.recommendedPieces,
    required this.exactPieces,
  });
  final WorkItem item;
  final DateTime start, end, pauseStart, pauseEnd, capacityEnd;
  final int wholePieces, recommendedPieces;
  final double exactPieces;
  int get remaining => item.quantity - wholePieces;
  int get productiveSeconds =>
      (wholePieces * item.minutesPerPiece * 60).round();
  int get lowerPieces => exactPieces.floor();
  int get upperPieces => math.min(item.quantity, exactPieces.ceil());
  bool get hasRoundingChoice =>
      exactPieces < item.quantity && lowerPieces != upperPieces;

  ScheduleStep copyWith({DateTime? start, DateTime? end}) => ScheduleStep(
    item: item,
    start: start ?? this.start,
    end: end ?? this.end,
    pauseStart: pauseStart,
    pauseEnd: pauseEnd,
    capacityEnd: capacityEnd,
    wholePieces: wholePieces,
    recommendedPieces: recommendedPieces,
    exactPieces: exactPieces,
  );

  Map<String, Object> toJson() => {
    'item': item.toJson(),
    'start': start.toIso8601String(),
    'end': end.toIso8601String(),
    'pauseStart': pauseStart.toIso8601String(),
    'pauseEnd': pauseEnd.toIso8601String(),
    'capacityEnd': capacityEnd.toIso8601String(),
    'wholePieces': wholePieces,
    'recommendedPieces': recommendedPieces,
    'exactPieces': exactPieces,
  };

  factory ScheduleStep.fromJson(Map<String, dynamic> json) => ScheduleStep(
    item: WorkItem.fromJson(Map<String, dynamic>.from(json['item'] as Map)),
    start: DateTime.parse(json['start'] as String),
    end: DateTime.parse(json['end'] as String),
    pauseStart: DateTime.parse(json['pauseStart'] as String),
    pauseEnd: DateTime.parse(json['pauseEnd'] as String),
    capacityEnd: DateTime.parse(
      json['capacityEnd'] as String? ?? json['end'] as String,
    ),
    wholePieces: json['wholePieces'] as int,
    recommendedPieces:
        json['recommendedPieces'] as int? ?? json['wholePieces'] as int,
    exactPieces: (json['exactPieces'] as num).toDouble(),
  );
}

class ShiftPlan {
  const ShiftPlan({
    required this.name,
    required this.shiftNumber,
    required this.startMinutes,
    this.overtimeHours = 0,
    required this.items,
  });
  final String name;
  final int shiftNumber, startMinutes, overtimeHours;
  final List<WorkItem> items;

  ShiftPlan copyWith({
    String? name,
    int? shiftNumber,
    int? startMinutes,
    int? overtimeHours,
    List<WorkItem>? items,
  }) => ShiftPlan(
    name: name ?? this.name,
    shiftNumber: shiftNumber ?? this.shiftNumber,
    startMinutes: startMinutes ?? this.startMinutes,
    overtimeHours: overtimeHours ?? this.overtimeHours,
    items: items ?? this.items,
  );

  Map<String, Object> toJson() => {
    'name': name,
    'shiftNumber': shiftNumber,
    'startMinutes': startMinutes,
    'overtimeHours': overtimeHours,
    'items': items.map((item) => item.toJson()).toList(),
  };

  factory ShiftPlan.fromJson(Map<String, dynamic> json) => ShiftPlan(
    name: json['name'] as String,
    shiftNumber: json['shiftNumber'] as int,
    startMinutes: json['startMinutes'] as int,
    overtimeHours: json['overtimeHours'] as int? ?? 0,
    items: (json['items'] as List)
        .map(
          (item) => WorkItem.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList(),
  );
}

List<ScheduleStep> calculateSchedule(ShiftPlan plan, DateTime date) {
  final template = ShiftTemplate.all.firstWhere(
    (s) => s.number == plan.shiftNumber,
  );
  final shift = template.onDate(
    date,
    customStartMinutes: plan.startMinutes,
    overtimeHours: plan.overtimeHours,
  );
  if (shift.start.isBefore(template.onDate(date).start) ||
      !shift.start.isBefore(shift.end)) {
    throw ArgumentError(
      'Der Arbeitsbeginn liegt nicht in der gewählten Schicht.',
    );
  }
  var cursor = shift.start;
  final result = <ScheduleStep>[];
  for (final item in plan.items) {
    if (!cursor.isBefore(shift.end)) break;
    final available = productiveMinutes(
      cursor,
      shift.end,
      shift.pauseStart,
      shift.pauseEnd,
    );
    final exact = math.min(
      item.quantity.toDouble(),
      available / item.minutesPerPiece,
    );
    final lower = exact.floor();
    final upper = math.min(item.quantity, exact.ceil());
    final fraction = exact - lower;
    final recommended = lower == upper || fraction < 0.5 ? lower : upper;
    final whole = switch (item.roundingChoice) {
      RoundingChoice.down => lower,
      RoundingChoice.up => upper,
      RoundingChoice.automatic => recommended,
    };
    final end = addProductiveMinutes(
      cursor,
      whole * item.minutesPerPiece,
      shift.pauseStart,
      shift.pauseEnd,
    );
    result.add(
      ScheduleStep(
        item: item,
        start: cursor,
        end: end,
        pauseStart: shift.pauseStart,
        pauseEnd: shift.pauseEnd,
        capacityEnd: shift.end,
        wholePieces: whole,
        recommendedPieces: recommended,
        exactPieces: exact,
      ),
    );
    cursor = end;
    if (whole < item.quantity) break;
  }
  return result;
}

double productiveMinutes(
  DateTime start,
  DateTime end,
  DateTime pauseStart,
  DateTime pauseEnd,
) {
  final total = end.difference(start).inSeconds / 60;
  final overlapStart = start.isAfter(pauseStart) ? start : pauseStart;
  final overlapEnd = end.isBefore(pauseEnd) ? end : pauseEnd;
  final pause = overlapEnd.isAfter(overlapStart)
      ? overlapEnd.difference(overlapStart).inSeconds / 60
      : 0;
  return math.max(0, total - pause);
}

DateTime addProductiveMinutes(
  DateTime start,
  double minutes,
  DateTime pauseStart,
  DateTime pauseEnd,
) {
  final beforePause = pauseStart.difference(start).inSeconds / 60;
  if (start.isBefore(pauseStart) && minutes > beforePause) {
    return pauseEnd.add(
      Duration(seconds: ((minutes - beforePause) * 60).round()),
    );
  }
  if (!start.isBefore(pauseStart) && start.isBefore(pauseEnd)) {
    return pauseEnd.add(Duration(seconds: (minutes * 60).round()));
  }
  return start.add(Duration(seconds: (minutes * 60).round()));
}

String hhmm(DateTime value) =>
    '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';

String durationClock(Duration value) {
  final seconds = value.inSeconds.abs();
  final hours = seconds ~/ 3600;
  final minutes = seconds % 3600 ~/ 60;
  final rest = seconds % 60;
  return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${rest.toString().padLeft(2, '0')}';
}
