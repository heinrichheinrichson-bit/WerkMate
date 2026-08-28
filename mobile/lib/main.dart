import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'domain.dart';
import 'plan_store.dart';

void main() => runApp(const WerkMateApp());

class WerkMateApp extends StatelessWidget {
  const WerkMateApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'WerkMate',
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xff2563eb),
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: const Color(0xfff6f7fb),
      cardTheme: const CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(20)),
          side: BorderSide(color: Color(0xffe4e7ec)),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(14)),
          borderSide: BorderSide(color: Color(0xffd0d5dd)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(0, 54),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
    ),
    home: const WerkMateHome(),
  );
}

class WerkMateHome extends StatefulWidget {
  const WerkMateHome({super.key});
  @override
  State<WerkMateHome> createState() => _WerkMateHomeState();
}

class _WerkMateHomeState extends State<WerkMateHome> {
  final store = PlanStore();
  int page = 1;
  List<ShiftPlan> saved = [];
  List<ScheduleStep> activeSteps = [];
  int runKey = 0;
  late ShiftPlan draft;

  @override
  void initState() {
    super.initState();
    draft = _emptyPlan();
    store.load().then((value) {
      if (mounted) setState(() => saved = value);
    });
  }

  ShiftPlan _emptyPlan() {
    final now = DateTime.now();
    final shift = ShiftTemplate.all.firstWhere((s) {
      final window = s.onDate(now);
      return !now.isBefore(window.start) && now.isBefore(window.end);
    }, orElse: () => ShiftTemplate.all.first);
    return ShiftPlan(
      name: '',
      shiftNumber: shift.number,
      startMinutes: shift.startHour * 60 + shift.startMinute,
      items: const [],
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text(
        'WerkMate',
        style: TextStyle(fontWeight: FontWeight.w800),
      ),
      centerTitle: false,
      actions: const [
        Padding(
          padding: EdgeInsets.only(right: 18),
          child: Center(
            child: Text(
              'Mobile 0.1',
              style: TextStyle(color: Color(0xff667085)),
            ),
          ),
        ),
      ],
    ),
    body: SafeArea(
      child: IndexedStack(
        index: page,
        children: [
          TodayPage(key: ValueKey(runKey), steps: activeSteps),
          PlanPage(
            plan: draft,
            onChanged: (value) => setState(() => draft = value),
            onSave: saveDraft,
            onStart: (steps) => setState(() {
              activeSteps = steps;
              runKey++;
              page = 0;
            }),
          ),
          PlansPage(
            plans: saved,
            onLoad: (plan) => setState(() {
              draft = plan.copyWith();
              page = 1;
            }),
            onDuplicate: duplicatePlan,
            onDelete: deletePlan,
          ),
          const MorePage(),
        ],
      ),
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: page,
      onDestinationSelected: (value) => setState(() => page = value),
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.timer_outlined),
          selectedIcon: Icon(Icons.timer),
          label: 'Heute',
        ),
        NavigationDestination(
          icon: Icon(Icons.view_timeline_outlined),
          selectedIcon: Icon(Icons.view_timeline),
          label: 'Planen',
        ),
        NavigationDestination(
          icon: Icon(Icons.bookmark_outline),
          selectedIcon: Icon(Icons.bookmark),
          label: 'Pläne',
        ),
        NavigationDestination(icon: Icon(Icons.more_horiz), label: 'Mehr'),
      ],
    ),
  );

  Future<void> saveDraft() async {
    final controller = TextEditingController(text: draft.name);
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Plan speichern'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Name des Plans'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Speichern'),
          ),
        ],
      ),
    );
    if (name == null || name.isEmpty || draft.items.isEmpty) return;
    final updated = draft.copyWith(name: name);
    final copy = [...saved];
    final index = copy.indexWhere((plan) => plan.name == name);
    if (index >= 0) {
      copy[index] = updated;
    } else {
      copy.add(updated);
    }
    await store.write(copy);
    if (mounted) {
      setState(() {
        draft = updated;
        saved = copy;
      });
    }
  }

  Future<void> duplicatePlan(ShiftPlan plan) async {
    var name = '${plan.name} Kopie';
    var suffix = 2;
    while (saved.any((item) => item.name == name)) {
      name = '${plan.name} Kopie $suffix';
      suffix++;
    }
    final copy = [...saved, plan.copyWith(name: name)];
    await store.write(copy);
    if (mounted) setState(() => saved = copy);
  }

  Future<void> deletePlan(ShiftPlan plan) async {
    final copy = saved.where((item) => item.name != plan.name).toList();
    await store.write(copy);
    if (mounted) setState(() => saved = copy);
  }
}

class PlanPage extends StatefulWidget {
  const PlanPage({
    super.key,
    required this.plan,
    required this.onChanged,
    required this.onSave,
    required this.onStart,
  });
  final ShiftPlan plan;
  final ValueChanged<ShiftPlan> onChanged;
  final VoidCallback onSave;
  final ValueChanged<List<ScheduleStep>> onStart;

  @override
  State<PlanPage> createState() => _PlanPageState();
}

class _PlanPageState extends State<PlanPage> {
  List<ScheduleStep> schedule = [];
  String? error;

  @override
  void didUpdateWidget(covariant PlanPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.plan, widget.plan)) _calculate();
  }

  @override
  Widget build(BuildContext context) {
    final template = ShiftTemplate.all.firstWhere(
      (s) => s.number == widget.plan.shiftNumber,
    );
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 28),
      children: [
        const PageTitle(
          title: 'Schicht planen',
          subtitle: 'Was möchtest du heute schaffen?',
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Schicht',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  initialValue: widget.plan.shiftNumber,
                  items: ShiftTemplate.all
                      .map(
                        (s) => DropdownMenuItem(
                          value: s.number,
                          child: Text(
                            '${s.name} · ${_hm(s.startHour, s.startMinute)}–${_hm(s.endHour, s.endMinute)}',
                          ),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value == null) return;
                    final selected = ShiftTemplate.all.firstWhere(
                      (s) => s.number == value,
                    );
                    _change(
                      widget.plan.copyWith(
                        shiftNumber: value,
                        startMinutes:
                            selected.startHour * 60 + selected.startMinute,
                      ),
                    );
                  },
                ),
                const SizedBox(height: 10),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.schedule),
                  title: const Text('Beginn der ersten Arbeit'),
                  subtitle: Text(_minutes(widget.plan.startMinutes)),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: _pickStart,
                ),
                Text(
                  'Feste Pause ${_hm(template.pauseHour, template.pauseMinute)}–${_hm(template.pauseEndHour, template.pauseEndMinute)} wird verrechnet.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: const Color(0xff667085),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Text(
              'Arbeiten',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
            const Spacer(),
            FilledButton.tonalIcon(
              onPressed: () => _editItem(),
              icon: const Icon(Icons.add),
              label: const Text('Hinzufügen'),
            ),
          ],
        ),
        const SizedBox(height: 10),
        if (widget.plan.items.isEmpty)
          const EmptyCard(
            icon: Icons.playlist_add,
            text: 'Füge deine erste Arbeit hinzu.',
          )
        else
          ReorderableListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: widget.plan.items.length,
            onReorderItem: (oldIndex, newIndex) {
              final items = [...widget.plan.items];
              final item = items.removeAt(oldIndex);
              items.insert(newIndex, item);
              _change(widget.plan.copyWith(items: items));
            },
            itemBuilder: (context, index) {
              final item = widget.plan.items[index];
              return Padding(
                key: ValueKey(item.id),
                padding: const EdgeInsets.only(bottom: 8),
                child: Card(
                  child: ListTile(
                    leading: CircleAvatar(child: Text('${index + 1}')),
                    title: Text(
                      item.name,
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    subtitle: Text(
                      '${item.quantity} Stück · ${_number(item.minutesPerPiece)} min/Stück',
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (value) {
                        if (value == 'edit') _editItem(index);
                        if (value == 'delete') {
                          final items = [...widget.plan.items]..removeAt(index);
                          _change(widget.plan.copyWith(items: items));
                        }
                      },
                      itemBuilder: (_) => const [
                        PopupMenuItem(value: 'edit', child: Text('Bearbeiten')),
                        PopupMenuItem(
                          value: 'delete',
                          child: Text('Entfernen'),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        if (schedule.isNotEmpty) ...[
          const SizedBox(height: 18),
          Text(
            'Soll-Ablauf',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          ...schedule.asMap().entries.map(
            (entry) => ScheduleCard(index: entry.key, step: entry.value),
          ),
        ],
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: widget.plan.items.isEmpty ? null : widget.onSave,
          icon: const Icon(Icons.bookmark_add_outlined),
          label: const Text('PLAN SPEICHERN'),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: schedule.isEmpty ? null : () => widget.onStart(schedule),
          icon: const Icon(Icons.arrow_forward),
          label: const Text('ZUM ARBEITSMODUS'),
        ),
      ],
    );
  }

  void _change(ShiftPlan plan) {
    widget.onChanged(plan);
    schedule = [];
    error = null;
    setState(() {});
    WidgetsBinding.instance.addPostFrameCallback((_) => _calculate());
  }

  void _calculate() {
    if (!mounted || widget.plan.items.isEmpty) {
      if (mounted) {
        setState(() {
          schedule = [];
          error = null;
        });
      }
      return;
    }
    try {
      final value = calculateSchedule(widget.plan, DateTime.now());
      setState(() {
        schedule = value;
        error = null;
      });
    } catch (e) {
      setState(() {
        schedule = [];
        error = e.toString().replaceFirst('Invalid argument(s): ', '');
      });
    }
  }

  Future<void> _pickStart() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(
        hour: widget.plan.startMinutes ~/ 60,
        minute: widget.plan.startMinutes % 60,
      ),
    );
    if (picked != null) {
      _change(
        widget.plan.copyWith(startMinutes: picked.hour * 60 + picked.minute),
      );
    }
  }

  Future<void> _editItem([int? index]) async {
    final current = index == null ? null : widget.plan.items[index];
    final result = await showModalBottomSheet<WorkItem>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) => WorkItemSheet(item: current),
    );
    if (result == null) return;
    final items = [...widget.plan.items];
    index == null ? items.add(result) : items[index] = result;
    _change(widget.plan.copyWith(items: items));
  }
}

class WorkItemSheet extends StatefulWidget {
  const WorkItemSheet({super.key, this.item});
  final WorkItem? item;
  @override
  State<WorkItemSheet> createState() => _WorkItemSheetState();
}

class _WorkItemSheetState extends State<WorkItemSheet> {
  late final TextEditingController name, quantity, minutes;
  String? error;
  @override
  void initState() {
    super.initState();
    name = TextEditingController(text: widget.item?.name ?? '');
    quantity = TextEditingController(
      text: widget.item?.quantity.toString() ?? '',
    );
    minutes = TextEditingController(
      text: widget.item == null ? '' : _number(widget.item!.minutesPerPiece),
    );
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.fromLTRB(
      20,
      18,
      20,
      20 + MediaQuery.viewInsetsOf(context).bottom,
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          widget.item == null ? 'Arbeit hinzufügen' : 'Arbeit bearbeiten',
          style: Theme.of(
            context,
          ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 18),
        TextField(
          controller: name,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Gesenknummer oder Bezeichnung',
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: quantity,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Gesamtstück'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: TextField(
                controller: minutes,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: 'min/Stück'),
              ),
            ),
          ],
        ),
        if (error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        const SizedBox(height: 18),
        FilledButton(onPressed: submit, child: const Text('ÜBERNEHMEN')),
      ],
    ),
  );
  void submit() {
    final amount = int.tryParse(quantity.text.trim());
    final pieceTime = double.tryParse(minutes.text.trim().replaceAll(',', '.'));
    if (amount == null || amount <= 0 || pieceTime == null || pieceTime <= 0) {
      setState(() => error = 'Bitte Gesamtstück und Stückzeit prüfen.');
      return;
    }
    Navigator.pop(
      context,
      WorkItem(
        id: widget.item?.id ?? DateTime.now().microsecondsSinceEpoch.toString(),
        name: name.text.trim().isEmpty ? 'Manuelle Arbeit' : name.text.trim(),
        quantity: amount,
        minutesPerPiece: pieceTime,
      ),
    );
  }
}

class TodayPage extends StatefulWidget {
  const TodayPage({super.key, required this.steps});
  final List<ScheduleStep> steps;
  @override
  State<TodayPage> createState() => _TodayPageState();
}

class _TodayPageState extends State<TodayPage> {
  int index = 0;
  DateTime? startedAt, targetEnd;
  Timer? timer;
  bool alarmed = false;
  DateTime now = DateTime.now();
  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.steps.isEmpty) return const EmptyToday();
    if (index >= widget.steps.length) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(28),
          child: EmptyCard(
            icon: Icons.task_alt,
            text: 'Alle geplanten Arbeiten beendet.',
          ),
        ),
      );
    }
    final step = widget.steps[index];
    final running = startedAt != null && targetEnd != null;
    final overdue = running && now.isAfter(targetEnd!);
    final difference = running ? targetEnd!.difference(now) : Duration.zero;
    final total = running
        ? targetEnd!.difference(startedAt!).inMilliseconds
        : 1;
    final elapsed = running ? now.difference(startedAt!).inMilliseconds : 0;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 28),
      children: [
        PageTitle(
          title: 'Heute',
          subtitle: running
              ? 'Aktuelle Arbeit läuft'
              : 'Bereit für deinen manuellen Start',
        ),
        const SizedBox(height: 18),
        Card(
          color: overdue ? const Color(0xffffe4e0) : null,
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Column(
              children: [
                Text(
                  '${index + 1} VON ${widget.steps.length}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: Color(0xff667085),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  step.item.name,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  '${step.wholePieces} Stück · ${_number(step.item.minutesPerPiece)} min/Stück',
                ),
                const SizedBox(height: 28),
                Text(
                  !running
                      ? 'NOCH NICHT GESTARTET'
                      : overdue
                      ? 'ÜBERZEIT'
                      : 'VERBLEIBEND',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    color: overdue
                        ? const Color(0xffb42318)
                        : const Color(0xff2563eb),
                  ),
                ),
                Text(
                  !running
                      ? '--:--:--'
                      : '${overdue ? '+ ' : ''}${durationClock(difference)}',
                  style: TextStyle(
                    fontSize: 46,
                    fontWeight: FontWeight.w900,
                    color: overdue
                        ? const Color(0xffb42318)
                        : const Color(0xff101828),
                  ),
                ),
                const SizedBox(height: 14),
                LinearProgressIndicator(
                  value: running ? (elapsed / total).clamp(0, 1) : 0,
                  minHeight: 10,
                  borderRadius: BorderRadius.circular(99),
                ),
                const SizedBox(height: 12),
                Text(
                  running
                      ? 'Start ${hhmm(startedAt!)} · Soll-Ende ${hhmm(targetEnd!)}'
                      : 'Start und Soll-Ende werden erst beim Start gesetzt.',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.skip_next)),
            title: const Text(
              'Danach',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            subtitle: Text(
              index + 1 < widget.steps.length
                  ? '${widget.steps[index + 1].item.name} · startet erst nach deiner Bestätigung'
                  : 'Keine weitere Arbeit geplant',
            ),
          ),
        ),
        const SizedBox(height: 18),
        if (!running)
          FilledButton.icon(
            onPressed: start,
            icon: const Icon(Icons.play_arrow),
            label: const Text('ARBEIT MANUELL STARTEN'),
          )
        else ...[
          FilledButton.icon(
            onPressed: finish,
            icon: const Icon(Icons.check),
            label: const Text('ARBEIT FERTIG'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: extend,
            icon: const Icon(Icons.more_time),
            label: const Text('ICH BRAUCHE LÄNGER'),
          ),
        ],
      ],
    );
  }

  void start() {
    final current = DateTime.now();
    final step = widget.steps[index];
    setState(() {
      startedAt = current;
      targetEnd = addProductiveMinutes(
        current,
        step.productiveSeconds / 60,
        step.pauseStart,
        step.pauseEnd,
      );
      now = current;
      alarmed = false;
    });
    timer?.cancel();
    timer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
  }

  void tick() {
    if (!mounted || targetEnd == null) return;
    setState(() => now = DateTime.now());
    if (!alarmed && !now.isBefore(targetEnd!)) {
      alarmed = true;
      SystemSound.play(SystemSoundType.alert);
      HapticFeedback.heavyImpact();
    }
  }

  void finish() {
    timer?.cancel();
    setState(() {
      index++;
      startedAt = null;
      targetEnd = null;
      alarmed = false;
    });
  }

  Future<void> extend() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(targetEnd!),
    );
    if (picked == null) return;
    var candidate = DateTime(
      now.year,
      now.month,
      now.day,
      picked.hour,
      picked.minute,
    );
    if (!candidate.isAfter(now)) {
      candidate = candidate.add(const Duration(days: 1));
    }
    setState(() {
      targetEnd = candidate;
      alarmed = false;
    });
  }
}

class PlansPage extends StatelessWidget {
  const PlansPage({
    super.key,
    required this.plans,
    required this.onLoad,
    required this.onDuplicate,
    required this.onDelete,
  });
  final List<ShiftPlan> plans;
  final ValueChanged<ShiftPlan> onLoad, onDuplicate, onDelete;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(16, 10, 16, 28),
    children: [
      const PageTitle(
        title: 'Meine Pläne',
        subtitle: 'Lokal auf diesem Gerät gespeichert',
      ),
      const SizedBox(height: 16),
      if (plans.isEmpty)
        const EmptyCard(
          icon: Icons.bookmark_border,
          text: 'Noch kein Schichtplan gespeichert.',
        ),
      ...plans.map(
        (plan) => Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Card(
            child: ListTile(
              contentPadding: const EdgeInsets.fromLTRB(18, 8, 8, 8),
              title: Text(
                plan.name,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                '${plan.items.length} Arbeiten · Start ${_minutes(plan.startMinutes)}',
              ),
              onTap: () => onLoad(plan),
              trailing: PopupMenuButton<String>(
                onSelected: (value) {
                  if (value == 'copy') onDuplicate(plan);
                  if (value == 'delete') onDelete(plan);
                },
                itemBuilder: (_) => const [
                  PopupMenuItem(value: 'copy', child: Text('Duplizieren')),
                  PopupMenuItem(value: 'delete', child: Text('Löschen')),
                ],
              ),
            ),
          ),
        ),
      ),
    ],
  );
}

class MorePage extends StatelessWidget {
  const MorePage({super.key});
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.fromLTRB(16, 10, 16, 28),
    children: const [
      PageTitle(
        title: 'Mehr',
        subtitle: 'Weitere Bereiche folgen schrittweise',
      ),
      SizedBox(height: 16),
      Card(
        child: Column(
          children: [
            ListTile(
              leading: Icon(Icons.precision_manufacturing_outlined),
              title: Text('Gesenkkatalog'),
              subtitle: Text('Als nächster Ausbauschritt'),
            ),
            Divider(height: 1),
            ListTile(
              leading: Icon(Icons.history),
              title: Text('Historie'),
              subtitle: Text('Nach der Stückrückmeldung'),
            ),
            Divider(height: 1),
            ListTile(
              leading: Icon(Icons.settings_outlined),
              title: Text('Einstellungen'),
            ),
          ],
        ),
      ),
    ],
  );
}

class ScheduleCard extends StatelessWidget {
  const ScheduleCard({super.key, required this.index, required this.step});
  final int index;
  final ScheduleStep step;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(child: Text('${index + 1}')),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          step.item.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                      ),
                      Text(
                        '${hhmm(step.start)}–${hhmm(step.end)}',
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${step.wholePieces} ganze Stück · ${_number(step.exactPieces)} rechnerisch',
                  ),
                  if (step.remaining > 0)
                    Text(
                      '${step.remaining} Stück bleiben offen',
                      style: const TextStyle(color: Color(0xffb54708)),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class PageTitle extends StatelessWidget {
  const PageTitle({super.key, required this.title, required this.subtitle});
  final String title, subtitle;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: Theme.of(
          context,
        ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w900),
      ),
      Text(subtitle, style: const TextStyle(color: Color(0xff667085))),
    ],
  );
}

class EmptyCard extends StatelessWidget {
  const EmptyCard({super.key, required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        children: [
          Icon(icon, size: 44, color: const Color(0xff98a2b3)),
          const SizedBox(height: 10),
          Text(text, textAlign: TextAlign.center),
        ],
      ),
    ),
  );
}

class EmptyToday extends StatelessWidget {
  const EmptyToday({super.key});
  @override
  Widget build(BuildContext context) => const Center(
    child: Padding(
      padding: EdgeInsets.all(24),
      child: EmptyCard(
        icon: Icons.timer_outlined,
        text: 'Noch kein Arbeitsablauf gestartet.\nPlane zuerst deine Schicht.',
      ),
    ),
  );
}

String _hm(int hour, int minute) =>
    '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';
String _minutes(int value) => _hm(value ~/ 60, value % 60);
String _number(double value) => value == value.roundToDouble()
    ? value.toStringAsFixed(0)
    : value.toStringAsFixed(1).replaceAll('.', ',');
