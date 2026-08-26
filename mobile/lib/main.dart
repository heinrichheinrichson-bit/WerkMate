import 'dart:math' as math;
import 'package:flutter/material.dart';

void main() => runApp(const WerkMateMobile());

class WerkMateMobile extends StatefulWidget {
  const WerkMateMobile({super.key});
  @override
  State<WerkMateMobile> createState() => _WerkMateMobileState();
}

class _WerkMateMobileState extends State<WerkMateMobile> {
  int page = 0;
  WorkRun? active;
  final history = <WorkReport>[];

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'WerkMate Mobile',
    theme: ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff14532d)),
      useMaterial3: true,
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
    ),
    home: Scaffold(
      appBar: AppBar(
        title: const Text(
          'WerkMate',
          style: TextStyle(fontWeight: FontWeight.w800),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: Center(child: Text('Mobile · 0.19.0')),
          ),
        ],
      ),
      body: SafeArea(
        child: IndexedStack(
          index: page,
          children: [
            ActivePage(active: active, onReport: reportActive),
            QuickStartPage(
              onStart: (run) => setState(() {
                active = run;
                page = 0;
              }),
            ),
            HistoryPage(history: history),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: page,
        onDestinationSelected: (value) => setState(() => page = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.timer_outlined),
            label: 'Laufend',
          ),
          NavigationDestination(
            icon: Icon(Icons.play_arrow),
            label: 'Schnellstart',
          ),
          NavigationDestination(icon: Icon(Icons.history), label: 'Historie'),
        ],
      ),
    ),
  );

  Future<void> reportActive() async {
    final run = active;
    if (run == null) return;
    final actual = TextEditingController(text: '${run.plannedPieces}');
    final reported = TextEditingController(text: '${run.plannedPieces}');
    final result = await showDialog<(int, int)>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Arbeitseinsatz rückmelden'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: actual,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Tatsächlich bearbeitet',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: reported,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Betrieblich rückgemeldet',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () {
              final a = int.tryParse(actual.text);
              final r = int.tryParse(reported.text);
              if (a != null && r != null && a >= 0 && r >= 0 && r <= a) {
                Navigator.pop(context, (a, r));
              }
            },
            child: const Text('Speichern'),
          ),
        ],
      ),
    );
    if (result == null) return;
    setState(() {
      history.insert(0, WorkReport(run, DateTime.now(), result.$1, result.$2));
      active = null;
      page = 2;
    });
  }
}

class ActivePage extends StatelessWidget {
  const ActivePage({super.key, required this.active, required this.onReport});
  final WorkRun? active;
  final VoidCallback onReport;
  @override
  Widget build(BuildContext context) {
    final run = active;
    if (run == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.task_alt, size: 64, color: Colors.grey),
              SizedBox(height: 16),
              Text(
                'Kein laufender Auftrag',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Unter „Schnellstart“ genügen Menge und Stückzeit.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }
    final overdue = DateTime.now().isAfter(run.targetEnd);
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          run.orderNumber,
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        Text(
          'Gesenk ${run.dieNumber} · ${run.minutesPerPiece.toStringAsFixed(1)} min/Stück',
        ),
        const SizedBox(height: 28),
        Card(
          color: overdue ? Theme.of(context).colorScheme.errorContainer : null,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                Text(
                  overdue ? 'RÜCKMELDUNG ÜBERFÄLLIG' : 'GEPLANTE RÜCKMELDUNG',
                ),
                const SizedBox(height: 8),
                Text(
                  clock(run.targetEnd),
                  style: const TextStyle(
                    fontSize: 42,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  '${run.plannedPieces} vollständige Stück für diesen Einsatz',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        InfoRow(label: 'Anmeldung', value: dateTime(run.startedAt)),
        InfoRow(label: 'Schichtende', value: dateTime(run.shiftEnd)),
        InfoRow(
          label: 'Schichtprognose',
          value: '${run.pieceEquivalent.toStringAsFixed(1)} Stück',
        ),
        const SizedBox(height: 24),
        FilledButton.icon(
          onPressed: onReport,
          icon: const Icon(Icons.check),
          label: const Padding(
            padding: EdgeInsets.symmetric(vertical: 14),
            child: Text('STÜCK RÜCKMELDEN'),
          ),
        ),
      ],
    );
  }
}

class QuickStartPage extends StatefulWidget {
  const QuickStartPage({super.key, required this.onStart});
  final ValueChanged<WorkRun> onStart;
  @override
  State<QuickStartPage> createState() => _QuickStartPageState();
}

class _QuickStartPageState extends State<QuickStartPage> {
  final quantity = TextEditingController();
  final minutes = TextEditingController();
  final die = TextEditingController();
  final order = TextEditingController();
  String? error;
  WorkRun? preview;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Text(
        'Schnellstart',
        style: Theme.of(
          context,
        ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
      ),
      const Text('Pflicht sind nur Menge und Stückzeit.'),
      const SizedBox(height: 20),
      Row(
        children: [
          Expanded(
            child: TextField(
              controller: quantity,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Gesamtmenge *'),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: TextField(
              controller: minutes,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: 'min/Stück *'),
            ),
          ),
        ],
      ),
      const SizedBox(height: 12),
      TextField(
        controller: die,
        decoration: const InputDecoration(labelText: 'Gesenknummer (optional)'),
      ),
      const SizedBox(height: 12),
      TextField(
        controller: order,
        decoration: const InputDecoration(
          labelText: 'Auftragsnummer (optional)',
        ),
      ),
      if (error != null)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Text(
            error!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ),
      const SizedBox(height: 16),
      OutlinedButton(
        onPressed: calculate,
        child: const Text('SCHICHT BERECHNEN'),
      ),
      if (preview case final run?) ...[
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${run.pieceEquivalent.toStringAsFixed(1)} Stück bis Schichtende',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text('Davon ${run.plannedPieces} Stück vollständig'),
                Text('Geplante Rückmeldung: ${dateTime(run.targetEnd)}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: () => widget.onStart(run),
          icon: const Icon(Icons.play_arrow),
          label: const Padding(
            padding: EdgeInsets.symmetric(vertical: 14),
            child: Text('ARBEIT STARTEN'),
          ),
        ),
      ],
    ],
  );

  void calculate() {
    final amount = int.tryParse(quantity.text.trim());
    final pieceTime = double.tryParse(minutes.text.trim().replaceAll(',', '.'));
    if (amount == null || amount <= 0 || pieceTime == null || pieceTime <= 0) {
      setState(
        () => error = 'Bitte eine gültige Menge und Stückzeit eingeben.',
      );
      return;
    }
    setState(() {
      error = null;
      preview = WorkRun.calculate(
        orderNumber: order.text.trim().isEmpty
            ? 'SCHNELL-${DateTime.now().millisecondsSinceEpoch}'
            : order.text.trim(),
        dieNumber: die.text.trim().isEmpty ? 'MANUELL' : die.text.trim(),
        totalQuantity: amount,
        minutesPerPiece: pieceTime,
        startedAt: DateTime.now(),
      );
    });
  }
}

class HistoryPage extends StatelessWidget {
  const HistoryPage({super.key, required this.history});
  final List<WorkReport> history;
  @override
  Widget build(BuildContext context) {
    if (history.isEmpty) {
      return const Center(child: Text('Noch keine mobilen Rückmeldungen.'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: history.length,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (_, index) {
        final item = history[index];
        final credit = item.actual - item.reported;
        return Card(
          child: ListTile(
            title: Text(
              item.run.orderNumber,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Text(
              '${dateTime(item.run.startedAt)} – ${clock(item.endedAt)}\nBearbeitet ${item.actual} · Gemeldet ${item.reported}',
            ),
            trailing: Text(
              'Guthaben\n${credit >= 0 ? '+' : ''}$credit',
              textAlign: TextAlign.center,
            ),
            isThreeLine: true,
          ),
        );
      },
    );
  }
}

class WorkRun {
  WorkRun(
    this.orderNumber,
    this.dieNumber,
    this.totalQuantity,
    this.minutesPerPiece,
    this.startedAt,
    this.shiftEnd,
    this.targetEnd,
    this.pieceEquivalent,
    this.plannedPieces,
  );
  final String orderNumber, dieNumber;
  final int totalQuantity, plannedPieces;
  final double minutesPerPiece, pieceEquivalent;
  final DateTime startedAt, shiftEnd, targetEnd;
  factory WorkRun.calculate({
    required String orderNumber,
    required String dieNumber,
    required int totalQuantity,
    required double minutesPerPiece,
    required DateTime startedAt,
  }) {
    final shift = shiftAt(startedAt);
    final productive = productiveMinutes(
      startedAt,
      shift.end,
      shift.pauseStart,
      shift.pauseEnd,
    );
    final equivalent = math.min(
      totalQuantity.toDouble(),
      productive / minutesPerPiece,
    );
    final whole = math.min(totalQuantity, math.max(1, equivalent.floor()));
    return WorkRun(
      orderNumber,
      dieNumber,
      totalQuantity,
      minutesPerPiece,
      startedAt,
      shift.end,
      addProductiveMinutes(
        startedAt,
        whole * minutesPerPiece,
        shift.pauseStart,
        shift.pauseEnd,
      ),
      equivalent,
      whole,
    );
  }
}

class WorkReport {
  WorkReport(this.run, this.endedAt, this.actual, this.reported);
  final WorkRun run;
  final DateTime endedAt;
  final int actual, reported;
}

class ShiftWindow {
  const ShiftWindow(this.end, this.pauseStart, this.pauseEnd);
  final DateTime end, pauseStart, pauseEnd;
}

ShiftWindow shiftAt(DateTime now) {
  DateTime at(int day, int hour, int minute) =>
      DateTime(now.year, now.month, now.day + day, hour, minute);
  if (!now.isBefore(at(0, 5, 45)) && now.isBefore(at(0, 13, 45))) {
    return ShiftWindow(at(0, 13, 45), at(0, 8, 45), at(0, 9, 3));
  }
  if (!now.isBefore(at(0, 13, 45)) && now.isBefore(at(0, 21, 45))) {
    return ShiftWindow(at(0, 21, 45), at(0, 17, 45), at(0, 18, 3));
  }
  if (now.isBefore(at(0, 5, 45))) {
    return ShiftWindow(at(0, 5, 45), at(0, 1, 45), at(0, 2, 3));
  }
  return ShiftWindow(at(1, 5, 45), at(1, 1, 45), at(1, 2, 3));
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

class InfoRow extends StatelessWidget {
  const InfoRow({super.key, required this.label, required this.value});
  final String label, value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
      ],
    ),
  );
}

String clock(DateTime value) =>
    '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
String dateTime(DateTime value) =>
    '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')}.${value.year} ${clock(value)}';
