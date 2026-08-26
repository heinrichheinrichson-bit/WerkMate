import 'package:flutter_test/flutter_test.dart';
import 'package:werkmate_mobile/main.dart';

void main() {
  testWidgets('WerkMate starts on the empty running page', (tester) async {
    await tester.pumpWidget(const WerkMateMobile());
    expect(find.text('Kein laufender Auftrag'), findsOneWidget);
    expect(find.text('Schnellstart'), findsOneWidget);
  });

  test('early shift forecast includes the fixed break', () {
    final run = WorkRun.calculate(
      orderNumber: 'FA',
      dieNumber: '8720',
      totalQuantity: 48,
      minutesPerPiece: 20,
      startedAt: DateTime(2026, 8, 26, 5, 45),
    );
    expect(run.pieceEquivalent, 23.1);
    expect(run.plannedPieces, 23);
    expect(run.targetEnd, DateTime(2026, 8, 26, 13, 43));
  });
}
