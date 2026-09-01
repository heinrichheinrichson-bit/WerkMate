import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:werkmate_mobile/domain.dart';
import 'package:werkmate_mobile/app_settings_store.dart';
import 'package:werkmate_mobile/card_scan.dart';
import 'package:werkmate_mobile/die_catalog_store.dart';
import 'package:werkmate_mobile/main.dart';
import 'package:werkmate_mobile/report_store.dart';
import 'package:werkmate_mobile/work_session_store.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('company card QR payload fills the order number', () {
    final scan = parseCardText('FA|4022377');
    expect(scan.orderNumber, '4022377');
    expect(scan.dieNumber, isNull);
    expect(scan.quantity, isNull);
  });

  test('die catalog is local, normalized and separated by operation', () async {
    final store = DieCatalogStore();
    await store.write(const [
      DieCatalogEntry(
        id: '1',
        dieNumber: '4583-00',
        operation: 'fp',
        minutesPerPiece: 12.5,
      ),
      DieCatalogEntry(
        id: '2',
        dieNumber: '4583-01',
        operation: 'ZP',
        minutesPerPiece: 15,
      ),
    ]);

    final loaded = await store.load();
    expect(loaded, hasLength(2));
    expect(loaded.first.normalizedDieNumber, '4583');
    expect(loaded.first.normalizedOperation, 'FP');
    expect(loaded.map((entry) => entry.key).toSet(), {'4583|FP', '4583|ZP'});
  });

  test('recognized card text can add die number and quantity', () {
    final scan = parseCardText('FA|4022377\nGN 4583-00\nGesamtmenge [FA] 24');
    expect(scan.orderNumber, '4022377');
    expect(scan.rawDieNumber, '4583-00');
    expect(scan.dieNumber, '4583');
    expect(scan.quantity, 24);
    expect(normalizeDieNumber('4583-01'), '4583');
  });

  test('standalone printed die number is recognized and normalized', () {
    final scan = parseCardText('FA|4022377\n4022377\n4583-00');
    expect(scan.rawDieNumber, '4583-00');
    expect(scan.dieNumber, '4583');
    expect(scan.quantity, isNull);
  });

  test('order number is never reused as die number', () {
    final scan = parseCardText('FA|4022377\nGN 4022377-00\n24\n24');
    expect(scan.orderNumber, '4022377');
    expect(scan.dieNumber, isNull);
    expect(scan.quantity, 24);
  });

  test('standalone die is fallback when GN is assigned to order by OCR', () {
    final scan = parseCardText(
      'FA|4022377\nGN\n4022377\nWerkstoff\n4583–00\nL334\n24\n24',
    );
    expect(scan.orderNumber, '4022377');
    expect(scan.dieNumber, '4583');
    expect(scan.quantity, 24);
  });

  test('repeated final card quantities are safely recognized', () {
    final scan = parseCardText(
      'FA|4022377\n4022377\n4583-00\nL334\nB24B52\n24\n24',
    );
    expect(scan.orderNumber, '4022377');
    expect(scan.dieNumber, '4583');
    expect(scan.quantity, 24);
  });

  test('a single unlabeled number is not guessed as quantity', () {
    final scan = parseCardText('FA|4022377\n4022377\n4583-00\n1\n824852');
    expect(scan.quantity, isNull);
  });

  test('work reports are stored locally with deviations', () async {
    final store = ReportStore();
    final report = WorkReport(
      id: 'report-1',
      item: const WorkItem(
        id: 'work-1',
        orderNumber: '40230747',
        dieNumber: '8720',
        operation: 'FP',
        quantity: 12,
        minutesPerPiece: 20,
      ),
      plannedPieces: 5,
      actualPieces: 6,
      reportedPieces: 5,
      startedAt: DateTime(2026, 8, 29, 5, 45),
      endedAt: DateTime(2026, 8, 29, 7, 35),
      plannedEnd: DateTime(2026, 8, 29, 7, 25),
      completedOrder: false,
      note: 'Testnotiz',
    );
    await store.append(report);

    final saved = await store.load();
    expect(saved, hasLength(1));
    expect(saved.single.item.orderNumber, '40230747');
    expect(saved.single.pieceDeviation, 1);
    expect(saved.single.timeDeviationMinutes, 10);
    expect(saved.single.note, 'Testnotiz');
    await store.delete('report-1');
    expect(await store.load(), isEmpty);
  });

  test('selected appearance is stored locally', () async {
    final store = AppSettingsStore();
    expect(await store.loadThemeMode(), ThemeMode.system);
    await store.saveThemeMode(ThemeMode.dark);
    expect(await store.loadThemeMode(), ThemeMode.dark);
  });

  testWidgets('history card shows colored time and piece deviations', (
    tester,
  ) async {
    final report = WorkReport(
      id: 'history-1',
      item: const WorkItem(
        id: 'work-history',
        dieNumber: '8720',
        quantity: 12,
        minutesPerPiece: 20,
      ),
      plannedPieces: 5,
      actualPieces: 6,
      reportedPieces: 5,
      plannedStart: DateTime(2026, 8, 29, 10),
      startedAt: DateTime(2026, 8, 29, 10),
      plannedEnd: DateTime(2026, 8, 29, 11, 40),
      endedAt: DateTime(2026, 8, 29, 11, 50),
      completedOrder: false,
      note: 'Werkzeug geprüft',
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ReportHistoryCard(report: report, onDelete: () {}),
        ),
      ),
    );
    await tester.tap(find.text('Ges. 8720'));
    await tester.pumpAndSettle();
    expect(find.textContaining('10 Min. Verzug'), findsOneWidget);
    expect(find.text('+1 Stück mehr als geplant'), findsOneWidget);
    expect(find.text('Notiz: Werkzeug geprüft'), findsOneWidget);
  });

  test('report time is never future and at most 59 minutes old', () {
    final now = DateTime(2026, 8, 29, 12);
    final start = DateTime(2026, 8, 29, 10);
    expect(
      validateReportTime(
        now: now,
        startedAt: start,
        reportedAt: DateTime(2026, 8, 29, 12, 1),
      ),
      contains('Zukunft'),
    );
    expect(
      validateReportTime(
        now: now,
        startedAt: start,
        reportedAt: DateTime(2026, 8, 29, 11),
      ),
      contains('59 Minuten'),
    );
    expect(
      validateReportTime(
        now: now,
        startedAt: start,
        reportedAt: DateTime(2026, 8, 29, 11, 1),
      ),
      isNull,
    );
    expect(
      validateReportTime(
        now: now,
        startedAt: DateTime(2026, 8, 29, 11, 30),
        reportedAt: DateTime(2026, 8, 29, 11, 29),
      ),
      contains('Startzeit'),
    );
  });

  test('credit is produced and can be partially consumed', () {
    const source = WorkItem(
      id: 'credit-source',
      orderNumber: '40245678',
      dieNumber: '1111',
      operation: 'FP',
      quantity: 10,
      minutesPerPiece: 15,
    );
    final base = DateTime(2026, 8, 29, 8);
    WorkReport report(WorkItem item, int actual, int reported) => WorkReport(
      id: '${item.id}-$actual-$reported',
      item: item,
      plannedPieces: 10,
      actualPieces: actual,
      reportedPieces: reported,
      startedAt: base,
      endedAt: base.add(const Duration(minutes: 10)),
      plannedEnd: base.add(const Duration(minutes: 10)),
      completedOrder: false,
      note: '',
    );

    final produced = report(source, 10, 5);
    final creditItem = WorkItem(
      id: 'credit-use',
      orderNumber: source.orderNumber,
      dieNumber: source.dieNumber,
      operation: source.operation,
      isCredit: true,
      quantity: 2,
      minutesPerPiece: source.minutesPerPiece,
    );
    final balances = calculateCreditBalances([
      produced,
      report(creditItem, 0, 2),
    ]);
    expect(balances, hasLength(1));
    expect(balances.single.availablePieces, 3);
    expect(balances.single.availableMinutes, 45);
  });

  test('using credit does not count as newly produced work', () {
    const source = WorkItem(
      id: 'source',
      orderNumber: '40245678',
      dieNumber: '1111',
      operation: 'FP',
      quantity: 10,
      minutesPerPiece: 15,
    );
    const credit = WorkItem(
      id: 'credit',
      orderNumber: '40245678',
      dieNumber: '1111',
      operation: 'FP',
      quantity: 5,
      minutesPerPiece: 15,
      isCredit: true,
    );
    final base = DateTime(2026, 8, 29, 8);
    WorkReport report(WorkItem item, int actual, int reported) => WorkReport(
      id: item.id,
      item: item,
      plannedPieces: item.quantity,
      actualPieces: actual,
      reportedPieces: reported,
      startedAt: base,
      endedAt: base,
      plannedEnd: base,
      completedOrder: false,
      note: '',
    );

    final totals = calculateWorkTotals([
      report(source, 10, 5),
      report(credit, 5, 5),
    ]);
    expect(totals.producedPieces, 10);
    expect(totals.reportedPieces, 10);
    expect(
      calculateCreditBalances([report(source, 10, 5), report(credit, 5, 5)]),
      isEmpty,
    );
  });

  test('partial work becomes credit but impossible totals do not', () {
    final base = DateTime(2026, 8, 29, 8);
    WorkReport report(int quantity, int actual, int reported) => WorkReport(
      id: '$quantity-$actual-$reported',
      item: WorkItem(
        id: 'invalid-$quantity',
        orderNumber: 'ORDER-$quantity',
        dieNumber: '1111',
        quantity: quantity,
        minutesPerPiece: 15,
      ),
      plannedPieces: actual,
      actualPieces: actual,
      reportedPieces: reported,
      startedAt: base,
      endedAt: base,
      plannedEnd: base,
      completedOrder: false,
      note: '',
    );

    final partial = calculateCreditBalances([report(20, 10, 5)]);
    expect(partial.single.availablePieces, 5);
    expect(calculateCreditBalances([report(10, 10, 15)]), isEmpty);
  });

  test('planned credit is reserved and cannot be offered twice', () {
    const item = WorkItem(
      id: 'source',
      orderNumber: '40245678',
      dieNumber: '1111',
      operation: 'FP',
      quantity: 10,
      minutesPerPiece: 15,
    );
    const balance = CreditBalance(
      item: item,
      producedPieces: 10,
      reportedPieces: 5,
    );
    const reservation = WorkItem(
      id: 'reserved',
      orderNumber: '40245678',
      dieNumber: '1111',
      operation: 'FP',
      isCredit: true,
      quantity: 5,
      minutesPerPiece: 15,
    );
    expect(reservePlannedCredits([balance], [reservation]), isEmpty);
  });

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
            activeDay: false,
            catalog: const [],
            onCatalogSave: (_) async {},
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

  testWidgets('active day is visible and finish requires confirmation', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    final steps = calculateSchedule(
      const ShiftPlan(
        name: 'Heute',
        shiftNumber: 1,
        startMinutes: 5 * 60 + 45,
        items: [
          WorkItem(
            id: '1',
            dieNumber: '1111',
            quantity: 2,
            minutesPerPiece: 10,
          ),
          WorkItem(
            id: '2',
            dieNumber: '2222',
            quantity: 2,
            minutesPerPiece: 10,
          ),
          WorkItem(
            id: '3',
            dieNumber: '3333',
            quantity: 2,
            minutesPerPiece: 10,
          ),
        ],
      ),
      DateTime(2099, 8, 28),
    );
    final restored = WorkSessionSnapshot(
      steps: steps,
      index: 0,
      startedAt: DateTime(2099, 8, 28, 5, 45),
      targetEnd: DateTime(2099, 8, 28, 6, 5),
    );
    WorkSessionSnapshot? changedSession;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TodayPage(
            steps: steps,
            restored: restored,
            catalog: const [],
            onCatalogSave: (_) async {},
            onSessionChanged: (value) => changedSession = value,
            onReport: (_) async {},
          ),
        ),
      ),
    );

    expect(find.text('Heutiger Ablauf'), findsOneWidget);
    expect(
      find.textContaining('bis zur geplanten Rückmeldung'),
      findsOneWidget,
    );
    expect(find.textContaining('von 20 Min.'), findsOneWidget);
    for (final die in ['Ges. 1111', 'Ges. 2222', 'Ges. 3333']) {
      expect(find.text(die), findsWidgets);
    }
    final moveUp = find.byTooltip('Eine Position nach oben').last;
    await tester.ensureVisible(moveUp);
    await tester.tap(moveUp);
    await tester.pump();
    expect(changedSession?.steps[1].item.dieNumber, '3333');
    expect(changedSession?.steps[2].item.dieNumber, '2222');
    await tester.ensureVisible(find.text('ARBEIT RÜCKMELDEN'));
    await tester.tap(find.text('ARBEIT RÜCKMELDEN'));
    await tester.pumpAndSettle();
    expect(find.text('Arbeit rückmelden'), findsOneWidget);
    expect(find.text('SPEICHERN UND ARBEIT BEENDEN'), findsOneWidget);
    await tester.tap(find.text('ABBRECHEN – ARBEIT WEITERLAUFEN LASSEN'));
    await tester.pumpAndSettle();
    expect(find.text('Arbeit rückmelden'), findsNothing);

    await tester.pumpWidget(const SizedBox());
    await tester.binding.setSurfaceSize(null);
  });

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
