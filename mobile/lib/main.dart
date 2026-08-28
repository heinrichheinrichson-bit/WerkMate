import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'domain.dart';
import 'alarm_service.dart';
import 'plan_store.dart';
import 'work_session_store.dart';

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
  final sessionStore = WorkSessionStore();
  int page = 1;
  List<ShiftPlan> saved = [];
  List<ScheduleStep> activeSteps = [];
  WorkSessionSnapshot? restoredSession;
  int runKey = 0;
  late ShiftPlan draft;

  @override
  void initState() {
    super.initState();
    draft = _emptyPlan();
    store.load().then((value) {
      if (mounted) setState(() => saved = value);
    });
    sessionStore.load().then((value) {
      if (mounted && value != null && value.index < value.steps.length) {
        setState(() {
          activeSteps = value.steps;
          restoredSession = value;
          runKey++;
        });
      }
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
              'Mobile 0.6',
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
          TodayPage(
            key: ValueKey(runKey),
            steps: activeSteps,
            restored: restoredSession,
            onSessionChanged: persistSession,
          ),
          PlanPage(
            plan: draft,
            onChanged: (value) => setState(() => draft = value),
            onSave: saveDraft,
            onStart: startPlan,
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

  Future<void> startPlan(List<ScheduleStep> steps) async {
    final snapshot = WorkSessionSnapshot(steps: steps, index: 0);
    await sessionStore.save(snapshot);
    if (!mounted) return;
    setState(() {
      activeSteps = steps;
      restoredSession = snapshot;
      runKey++;
      page = 0;
    });
  }

  Future<void> persistSession(WorkSessionSnapshot? snapshot) async {
    if (snapshot == null || snapshot.index >= snapshot.steps.length) {
      await sessionStore.clear();
    } else {
      await sessionStore.save(snapshot);
    }
    restoredSession = snapshot;
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
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _calculate());
  }

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
    final shift = template.onDate(
      DateTime.now(),
      customStartMinutes: widget.plan.startMinutes,
      overtimeHours: widget.plan.overtimeHours,
    );
    final productiveHours =
        productiveMinutes(
          shift.start,
          shift.end,
          shift.pauseStart,
          shift.pauseEnd,
        ) /
        60;
    final capacityMinutes = productiveHours * 60;
    final totalWorkMinutes = widget.plan.items.fold<double>(
      0,
      (total, item) => total + item.quantity * item.minutesPerPiece,
    );
    final plannedMinutes = schedule.fold<double>(
      0,
      (total, step) => total + step.wholePieces * step.item.minutesPerPiece,
    );
    final remainingWorkMinutes = (totalWorkMinutes - plannedMinutes).clamp(
      0.0,
      double.infinity,
    );
    final openMinutes = capacityMinutes - plannedMinutes;
    final overplanned = openMinutes < 0;
    final planProgress = capacityMinutes <= 0
        ? 0.0
        : (plannedMinutes / capacityMinutes).clamp(0.0, 1.0);
    return ResponsivePage(
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
                const Divider(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Überstunden',
                            style: TextStyle(fontWeight: FontWeight.w700),
                          ),
                          Text(
                            widget.plan.overtimeHours == 0
                                ? 'Normal · Ende ${hhmm(shift.end)} · ${_number(productiveHours)} Std. produktiv'
                                : '+${widget.plan.overtimeHours} Std. · Ende ${hhmm(shift.end)} · ${_number(productiveHours)} Std. produktiv',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    IconButton.filledTonal(
                      tooltip: 'Eine Überstunde entfernen',
                      onPressed: widget.plan.overtimeHours == 0
                          ? null
                          : () => _setOvertime(widget.plan.overtimeHours - 1),
                      icon: const Icon(Icons.remove),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: Text(
                        '+${widget.plan.overtimeHours}',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    IconButton.filled(
                      tooltip: 'Eine Überstunde hinzufügen',
                      onPressed: () =>
                          _setOvertime(widget.plan.overtimeHours + 1),
                      icon: const Icon(Icons.add),
                    ),
                  ],
                ),
                if (widget.plan.overtimeHours > 0)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => _setOvertime(0),
                      child: const Text('Auf Normalzeit zurücksetzen'),
                    ),
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
                      '${item.quantity} Stück · ${_number(item.minutesPerPiece)} min/Stück · ${_number(item.quantity * item.minutesPerPiece)} Min. gesamt',
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
        const SizedBox(height: 14),
        Card(
          color: overplanned ? const Color(0xffffe4e0) : null,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Expanded(
                      child: Text(
                        'Schichtbelegung',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    Text(
                      '${_number(plannedMinutes)} / ${_number(capacityMinutes)} Min.',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                LinearProgressIndicator(
                  value: planProgress,
                  minHeight: 10,
                  borderRadius: BorderRadius.circular(99),
                  color: overplanned ? const Color(0xffd92d20) : null,
                ),
                const SizedBox(height: 10),
                Text(
                  overplanned
                      ? '${_number(openMinutes.abs())} Min. über die Schicht hinaus verplant'
                      : openMinutes == 0
                      ? 'Schicht vollständig verplant'
                      : 'Noch ${_number(openMinutes)} Min. zu verplanen',
                  style: TextStyle(
                    color: overplanned
                        ? const Color(0xffb42318)
                        : const Color(0xff344054),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (remainingWorkMinutes > 0) ...[
                  const SizedBox(height: 6),
                  Text(
                    '${_number(remainingWorkMinutes)} Min. Auftragsvolumen bleiben für später offen',
                    style: const TextStyle(color: Color(0xff667085)),
                  ),
                ],
              ],
            ),
          ),
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
            (entry) => ScheduleCard(
              index: entry.key,
              step: entry.value,
              onRoundingChanged: (choice) => _setRounding(entry.key, choice),
            ),
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

  void _setOvertime(int hours) {
    _change(widget.plan.copyWith(overtimeHours: hours.clamp(0, 12)));
  }

  void _setRounding(int index, RoundingChoice choice) {
    final items = [...widget.plan.items];
    items[index] = items[index].copyWith(roundingChoice: choice);
    _change(widget.plan.copyWith(items: items));
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
  late final TextEditingController orderNumber, dieNumber, operation;
  late final TextEditingController quantity, minutes;
  String? error;
  @override
  void initState() {
    super.initState();
    orderNumber = TextEditingController(text: widget.item?.orderNumber ?? '');
    dieNumber = TextEditingController(text: widget.item?.dieNumber ?? '');
    operation = TextEditingController(text: widget.item?.operation ?? '');
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
          controller: dieNumber,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Gesenknummer'),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: orderNumber,
                decoration: const InputDecoration(
                  labelText: 'Auftragsnummer (optional)',
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: TextField(
                controller: operation,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(
                  labelText: 'Arbeitsgang',
                  hintText: 'z. B. FP',
                ),
              ),
            ),
          ],
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
        orderNumber: orderNumber.text.trim(),
        dieNumber: dieNumber.text.trim(),
        operation: operation.text.trim().toUpperCase(),
        roundingChoice: widget.item?.roundingChoice ?? RoundingChoice.automatic,
        quantity: amount,
        minutesPerPiece: pieceTime,
      ),
    );
  }
}

class TodayPage extends StatefulWidget {
  const TodayPage({
    super.key,
    required this.steps,
    required this.restored,
    required this.onSessionChanged,
  });
  final List<ScheduleStep> steps;
  final WorkSessionSnapshot? restored;
  final ValueChanged<WorkSessionSnapshot?> onSessionChanged;
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
  void initState() {
    super.initState();
    final restored = widget.restored;
    if (restored != null && restored.steps.isNotEmpty) {
      index = restored.index;
      startedAt = restored.startedAt;
      targetEnd = restored.targetEnd;
      if (restored.isRunning) {
        timer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
      }
    }
  }

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
    return ResponsivePage(
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
          if (overdue) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: silenceAlarm,
              icon: const Icon(Icons.notifications_off_outlined),
              label: const Text('ALARM STUMMSCHALTEN'),
            ),
          ],
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
    final snapshot = _snapshot();
    widget.onSessionChanged(snapshot);
    AlarmService.instance.requestPermissions().then((_) {
      if (targetEnd != null) {
        AlarmService.instance.schedule(targetEnd!, step.item.name);
      }
    });
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
    AlarmService.instance.cancel();
    setState(() {
      index++;
      startedAt = null;
      targetEnd = null;
      alarmed = false;
    });
    widget.onSessionChanged(index >= widget.steps.length ? null : _snapshot());
  }

  void silenceAlarm() {
    AlarmService.instance.cancel();
    setState(() => alarmed = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Alarm stumm – die aktuelle Arbeit läuft weiter.'),
      ),
    );
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
    widget.onSessionChanged(_snapshot());
    AlarmService.instance.schedule(candidate, widget.steps[index].item.name);
  }

  WorkSessionSnapshot _snapshot() => WorkSessionSnapshot(
    steps: widget.steps,
    index: index,
    startedAt: startedAt,
    targetEnd: targetEnd,
  );
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
  Widget build(BuildContext context) => ResponsivePage(
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
  Widget build(BuildContext context) => ResponsivePage(
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
  const ScheduleCard({
    super.key,
    required this.index,
    required this.step,
    required this.onRoundingChanged,
  });
  final int index;
  final ScheduleStep step;
  final ValueChanged<RoundingChoice> onRoundingChanged;
  @override
  Widget build(BuildContext context) {
    final lowerEnd = addProductiveMinutes(
      step.start,
      step.lowerPieces * step.item.minutesPerPiece,
      step.pauseStart,
      step.pauseEnd,
    );
    final upperEnd = addProductiveMinutes(
      step.start,
      step.upperPieces * step.item.minutesPerPiece,
      step.pauseStart,
      step.pauseEnd,
    );
    final lowerFree = step.capacityEnd.difference(lowerEnd);
    final upperOver = upperEnd.difference(step.capacityEnd);
    return Padding(
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
                      '${step.wholePieces} Stück geplant · ${_number(step.exactPieces)} rechnerisch',
                    ),
                    if (step.hasRoundingChoice) ...[
                      const SizedBox(height: 10),
                      Text(
                        'Stückzahl wählen:',
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          ChoiceChip(
                            selected: step.wholePieces == step.lowerPieces,
                            onSelected: (_) =>
                                onRoundingChanged(RoundingChoice.down),
                            label: Text(
                              '${step.lowerPieces} Stk · bis ${hhmm(lowerEnd)}\n${_number(lowerFree.inSeconds / 60)} Min. frei${step.recommendedPieces == step.lowerPieces ? ' · empfohlen' : ''}',
                            ),
                          ),
                          ChoiceChip(
                            selected: step.wholePieces == step.upperPieces,
                            onSelected: (_) =>
                                onRoundingChanged(RoundingChoice.up),
                            label: Text(
                              '${step.upperPieces} Stk · bis ${hhmm(upperEnd)}\n${_number(upperOver.inSeconds / 60)} Min. länger${step.recommendedPieces == step.upperPieces ? ' · empfohlen' : ''}',
                            ),
                          ),
                        ],
                      ),
                    ],
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
}

class ResponsivePage extends StatelessWidget {
  const ResponsivePage({super.key, required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) => ListView(
      padding: EdgeInsets.fromLTRB(
        constraints.maxWidth >= 700 ? 28 : 16,
        10,
        constraints.maxWidth >= 700 ? 28 : 16,
        28,
      ),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: children,
            ),
          ),
        ),
      ],
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
