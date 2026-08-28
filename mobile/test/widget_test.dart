import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:werkmate_mobile/domain.dart';
import 'package:werkmate_mobile/main.dart';
import 'package:werkmate_mobile/work_session_store.dart';

void main() {
  test('work identity separates order, die and operation', () {
    const item = WorkItem(
      id: '1',
      orderNumber: '40230747',
      dieNumber: '8720',
      operation: 'fp',
      quantity: 12,
      minutesPerPiece: 20,
    );
    expect(item.name, 'Auftrag 40230747 · Ges. 8720 · FP');
    expect(WorkItem.fromJson(item.toJson()).operation, 'fp');
  });

  test('old saved work names remain readable', () {
    final item = WorkItem.fromJson({
      'id': 'old',
      'name': '8720',
      'quantity': 12,
      'minutesPerPiece': 20,
    });
    expect(item.dieNumber, '8720');
  });

  test('whole overtime hours extend shift capacity and planned end', () {
    const work = WorkItem(
      id: '1',
      dieNumber: '4261',
      quantity: 40,
      minutesPerPiece: 15,
    );
    const normal = ShiftPlan(
      name: 'Normal',
      shiftNumber: 1,
      startMinutes: 5 * 60 + 45,
      items: [work],
    );
    final overtime = normal.copyWith(overtimeHours: 1);
    final normalStep = calculateSchedule(normal, DateTime(2026, 8, 28)).single;
    final overtimeStep = calculateSchedule(
      overtime,
      DateTime(2026, 8, 28),
    ).single;

    expect(normalStep.wholePieces, 31);
    expect(overtimeStep.wholePieces, 35);
    expect(overtimeStep.exactPieces, closeTo(34.8, 0.001));
    expect(
      hhmm(
        ShiftTemplate.all.first
            .onDate(DateTime(2026, 8, 28), overtimeHours: 1)
            .end,
      ),
      '14:45',
    );
    expect(ShiftPlan.fromJson(overtime.toJson()).overtimeHours, 1);
  });

  test('5.6 pieces recommends six but still allows five', () {
    const items = [
      WorkItem(id: '1', dieNumber: '1111', quantity: 10, minutesPerPiece: 15),
      WorkItem(id: '2', dieNumber: '1111', quantity: 10, minutesPerPiece: 20),
      WorkItem(id: '3', dieNumber: '8720', quantity: 40, minutesPerPiece: 20),
    ];
    const automatic = ShiftPlan(
      name: 'Rundung',
      shiftNumber: 2,
      startMinutes: 13 * 60 + 45,
      items: items,
    );
    final recommended = calculateSchedule(
      automatic,
      DateTime(2026, 8, 28),
    ).last;
    final downItems = [...items];
    downItems[2] = downItems[2].copyWith(roundingChoice: RoundingChoice.down);
    final roundedDown = calculateSchedule(
      automatic.copyWith(items: downItems),
      DateTime(2026, 8, 28),
    ).last;

    expect(recommended.exactPieces, closeTo(5.6, 0.001));
    expect(recommended.recommendedPieces, 6);
    expect(recommended.wholePieces, 6);
    expect(recommended.end, DateTime(2026, 8, 28, 21, 53));
    expect(roundedDown.wholePieces, 5);
    expect(roundedDown.end, DateTime(2026, 8, 28, 21, 33));
  });

  testWidgets('planning shows occupied and still open shift minutes', (
    tester,
  ) async {
    const plan = ShiftPlan(
      name: 'Fünf Stunden',
      shiftNumber: 1,
      startMinutes: 5 * 60 + 45,
      items: [
        WorkItem(id: '1', dieNumber: '5555', quantity: 20, minutesPerPiece: 15),
      ],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PlanPage(
            plan: plan,
            onChanged: (_) {},
            onSave: () {},
            onStart: (_) {},
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('300 / 462 Min.'), findsOneWidget);
    expect(find.text('Noch 162 Min. zu verplanen'), findsOneWidget);
    expect(find.textContaining('300 Min. gesamt'), findsOneWidget);
  });

  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('starts with smartphone planning navigation', (tester) async {
    await tester.pumpWidget(const WerkMateApp());
    await tester.pumpAndSettle();
    expect(find.text('Schicht planen'), findsOneWidget);
    for (final label in ['Heute', 'Planen', 'Pläne', 'Mehr']) {
      expect(find.text(label), findsOneWidget);
    }
  });

  testWidgets('planning page renders in phone landscape and tablet sizes', (
    tester,
  ) async {
    for (final size in [const Size(800, 400), const Size(1200, 800)]) {
      await tester.binding.setSurfaceSize(size);
      await tester.pumpWidget(const WerkMateApp());
      await tester.pumpAndSettle();
      expect(find.text('Schicht planen'), findsOneWidget);
      expect(tester.takeException(), isNull);
    }
    await tester.binding.setSurfaceSize(null);
  });

  test('multiple jobs fill the remaining early shift in sequence', () {
    final plan = ShiftPlan(
      name: 'Test',
      shiftNumber: 1,
      startMinutes: 5 * 60 + 45,
      items: const [
        WorkItem(id: '1', dieNumber: '8720', quantity: 12, minutesPerPiece: 20),
        WorkItem(id: '2', dieNumber: '4261', quantity: 40, minutesPerPiece: 15),
      ],
    );
    final result = calculateSchedule(plan, DateTime(2026, 8, 28));
    expect(result[0].start, DateTime(2026, 8, 28, 5, 45));
    expect(result[0].end, DateTime(2026, 8, 28, 10, 3));
    expect(result[0].wholePieces, 12);
    expect(result[1].start, DateTime(2026, 8, 28, 10, 3));
    expect(result[1].end, DateTime(2026, 8, 28, 13, 48));
    expect(result[1].wholePieces, 15);
    expect(result[1].exactPieces, 14.8);
    expect(result[1].remaining, 25);
  });

  test('night shift calculation crosses midnight', () {
    final plan = ShiftPlan(
      name: 'Nacht',
      shiftNumber: 3,
      startMinutes: 21 * 60 + 45,
      items: const [
        WorkItem(id: '1', dieNumber: '4261', quantity: 40, minutesPerPiece: 15),
      ],
    );
    final result = calculateSchedule(plan, DateTime(2026, 8, 28)).single;
    expect(result.wholePieces, 31);
    expect(result.exactPieces, 30.8);
    expect(result.end, DateTime(2026, 8, 29, 5, 48));
  });

  test('active work survives an app restart', () async {
    final steps = calculateSchedule(
      const ShiftPlan(
        name: 'Test',
        shiftNumber: 1,
        startMinutes: 345,
        items: [
          WorkItem(
            id: '1',
            dieNumber: '8720',
            quantity: 12,
            minutesPerPiece: 20,
          ),
        ],
      ),
      DateTime(2026, 8, 28),
    );
    final store = WorkSessionStore();
    final snapshot = WorkSessionSnapshot(
      steps: steps,
      index: 0,
      startedAt: DateTime(2026, 8, 28, 5, 45),
      targetEnd: DateTime(2026, 8, 28, 10, 3),
    );
    await store.save(snapshot);
    final restored = await store.load();
    expect(restored?.isRunning, isTrue);
    expect(restored?.steps.single.item.dieNumber, '8720');
    expect(restored?.targetEnd, DateTime(2026, 8, 28, 10, 3));
  });
}
