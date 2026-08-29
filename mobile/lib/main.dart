import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'domain.dart';
import 'alarm_service.dart';
import 'app_settings_store.dart';
import 'plan_store.dart';
import 'report_store.dart';
import 'work_session_store.dart';

void main() => runApp(const WerkMateApp());

class WerkMateApp extends StatefulWidget {
  const WerkMateApp({super.key});

  @override
  State<WerkMateApp> createState() => _WerkMateAppState();
}

class _WerkMateAppState extends State<WerkMateApp> {
  final settingsStore = AppSettingsStore();
  ThemeMode themeMode = ThemeMode.system;

  @override
  void initState() {
    super.initState();
    settingsStore.loadThemeMode().then((value) {
      if (mounted) setState(() => themeMode = value);
    });
  }

  Future<void> changeTheme(ThemeMode value) async {
    await settingsStore.saveThemeMode(value);
    if (mounted) setState(() => themeMode = value);
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'WerkMate',
    themeMode: themeMode,
    theme: _appTheme(Brightness.light),
    darkTheme: _appTheme(Brightness.dark),
    home: WerkMateHome(themeMode: themeMode, onThemeChanged: changeTheme),
  );
}

ThemeData _appTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  return ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: const Color(0xff2563eb),
      brightness: brightness,
    ),
    scaffoldBackgroundColor: dark
        ? const Color(0xff101318)
        : const Color(0xfff6f7fb),
    cardTheme: CardThemeData(
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: const BorderRadius.all(Radius.circular(20)),
        side: BorderSide(
          color: dark ? const Color(0xff344054) : const Color(0xffe4e7ec),
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: dark ? const Color(0xff1d2939) : Colors.white,
      border: const OutlineInputBorder(
        borderRadius: BorderRadius.all(Radius.circular(14)),
        borderSide: BorderSide(color: Color(0xffd0d5dd)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(0, 54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
      ),
    ),
  );
}

class WerkMateHome extends StatefulWidget {
  const WerkMateHome({
    super.key,
    required this.themeMode,
    required this.onThemeChanged,
  });
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode> onThemeChanged;
  @override
  State<WerkMateHome> createState() => _WerkMateHomeState();
}

class _WerkMateHomeState extends State<WerkMateHome> {
  final store = PlanStore();
  final sessionStore = WorkSessionStore();
  final reportStore = ReportStore();
  int page = 1;
  List<ShiftPlan> saved = [];
  List<WorkReport> reports = [];
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
    reportStore.load().then((value) {
      if (mounted) setState(() => reports = value);
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
              'Mobile 0.13',
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
            onReport: saveReport,
          ),
          PlanPage(
            plan: draft,
            activeDay: activeSteps.isNotEmpty && restoredSession != null,
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
          MorePage(
            reportCount: reports.length,
            creditCount: calculateCreditBalances(reports).length,
            onHistory: openHistory,
            onCredits: openCredits,
            onSettings: openSettings,
          ),
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
    if (activeSteps.isNotEmpty && restoredSession != null) {
      final replace = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          icon: const Icon(Icons.warning_amber_rounded),
          title: const Text('Laufenden Arbeitstag ersetzen?'),
          content: const Text(
            'Der aktuelle Auftrag, Countdown und Tagesablauf würden beendet. Das kann nicht rückgängig gemacht werden.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('ABBRECHEN'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.error,
              ),
              onPressed: () => Navigator.pop(context, true),
              child: const Text('VERWERFEN UND ERSETZEN'),
            ),
          ],
        ),
      );
      if (replace != true) return;
      await AlarmService.instance.cancel();
    }
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
    if (mounted) {
      setState(() {
        restoredSession = snapshot;
        if (snapshot == null) activeSteps = [];
      });
    }
  }

  Future<void> saveReport(WorkReport report) async {
    if (report.item.isCredit) {
      final balances = calculateCreditBalances(reports);
      final matching = balances.where(
        (balance) => sameWorkIdentity(balance.item, report.item),
      );
      final available = matching.isEmpty ? 0 : matching.first.availablePieces;
      if (report.reportedPieces > available) {
        throw StateError(
          'Nur $available Stück Guthaben sind aktuell verfügbar.',
        );
      }
    }
    await reportStore.append(report);
    final value = await reportStore.load();
    if (mounted) setState(() => reports = value);
  }

  Future<void> openHistory() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(builder: (context) => const HistoryPage()),
    );
    final value = await reportStore.load();
    if (mounted) setState(() => reports = value);
  }

  Future<void> openSettings() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (context) => SettingsPage(
          themeMode: widget.themeMode,
          onThemeChanged: widget.onThemeChanged,
        ),
      ),
    );
  }

  Future<void> openCredits() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (context) => CreditPage(
          balances: calculateCreditBalances(reports),
          onPlan: addCreditToPlan,
        ),
      ),
    );
  }

  void addCreditToPlan(CreditBalance balance, int pieces) {
    final source = balance.item;
    final credit = WorkItem(
      id: 'credit-${DateTime.now().microsecondsSinceEpoch}',
      orderNumber: source.orderNumber,
      dieNumber: source.dieNumber,
      operation: source.operation,
      isCredit: true,
      quantity: pieces,
      minutesPerPiece: source.minutesPerPiece,
    );
    setState(() {
      draft = draft.copyWith(items: [...draft.items, credit]);
      page = 1;
    });
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$pieces Stück Guthaben zur Planung hinzugefügt.'),
      ),
    );
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
    required this.activeDay,
    required this.onChanged,
    required this.onSave,
    required this.onStart,
  });
  final ShiftPlan plan;
  final bool activeDay;
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
        if (widget.activeDay) ...[
          const SizedBox(height: 12),
          const Card(
            color: Color(0xfffff4d6),
            child: ListTile(
              leading: Icon(Icons.lock_clock),
              title: Text(
                'Ein Arbeitstag läuft',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
              subtitle: Text(
                'Diese Planung ist nur ein Entwurf und verändert den laufenden Ablauf nicht.',
              ),
            ),
          ),
        ],
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
                      '${item.isCredit ? 'Guthaben · ' : ''}${item.quantity} Stück · ${_number(item.minutesPerPiece)} min/Stück · ${_number(item.quantity * item.minutesPerPiece)} Min. gesamt',
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
          icon: Icon(
            widget.activeDay ? Icons.shield_outlined : Icons.arrow_forward,
          ),
          label: Text(
            widget.activeDay ? 'AKTIVEN TAG ERSETZEN …' : 'ZUM ARBEITSMODUS',
          ),
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
    required this.onReport,
  });
  final List<ScheduleStep> steps;
  final WorkSessionSnapshot? restored;
  final ValueChanged<WorkSessionSnapshot?> onSessionChanged;
  final Future<void> Function(WorkReport) onReport;
  @override
  State<TodayPage> createState() => _TodayPageState();
}

class _TodayPageState extends State<TodayPage> {
  int index = 0;
  DateTime? startedAt, targetEnd;
  DateTime? snoozeUntil;
  Timer? timer;
  bool alarmed = false;
  DateTime now = DateTime.now();
  late List<ScheduleStep> steps;

  @override
  void initState() {
    super.initState();
    final restored = widget.restored;
    steps = List.of(restored?.steps ?? widget.steps);
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
    if (steps.isEmpty) return const EmptyToday();
    if (index >= steps.length) {
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
    final step = steps[index];
    final running = startedAt != null && targetEnd != null;
    final overdue = running && now.isAfter(targetEnd!);
    final difference = running ? targetEnd!.difference(now) : Duration.zero;
    final total = running
        ? targetEnd!.difference(startedAt!).inMilliseconds
        : 1;
    final elapsed = running ? now.difference(startedAt!).inMilliseconds : 0;
    final progress = running && total > 0
        ? (elapsed / total).clamp(0.0, 1.0)
        : 0.0;
    final totalMinutes = running ? (total / 60000).ceil() : 0;
    final elapsedMinutes = running
        ? (elapsed.clamp(0, total > 0 ? total : 0) / 60000).floor()
        : 0;
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
                  '${index + 1} VON ${steps.length}',
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
                        : Theme.of(context).colorScheme.onSurface,
                  ),
                ),
                if (running) ...[
                  const SizedBox(height: 4),
                  Text(
                    overdue
                        ? '${(difference.inSeconds.abs() / 60).ceil()} Min. über der geplanten Rückmeldezeit'
                        : 'Noch ${(difference.inSeconds / 60).ceil()} Min. bis zur geplanten Rückmeldung',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ],
                const SizedBox(height: 14),
                LinearProgressIndicator(
                  value: progress,
                  minHeight: 14,
                  borderRadius: BorderRadius.circular(99),
                ),
                const SizedBox(height: 8),
                if (running)
                  Text(
                    '${(progress * 100).floor()} % · $elapsedMinutes von $totalMinutes Min.',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                const SizedBox(height: 8),
                Text(
                  running
                      ? 'Soll ${hhmm(step.start)}–${hhmm(targetEnd!)} · gestartet ${hhmm(startedAt!)}'
                      : 'Start und Soll-Ende werden erst beim Start gesetzt.',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: ExpansionTile(
            initiallyExpanded: true,
            leading: const CircleAvatar(child: Icon(Icons.view_timeline)),
            title: const Text(
              'Heutiger Ablauf',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            subtitle: Text('${index + 1} von ${steps.length} aktiv'),
            children: [
              const Divider(height: 1),
              ...steps.asMap().entries.map((entry) {
                final position = entry.key;
                final planned = entry.value;
                final isDone = position < index;
                final isCurrent = position == index;
                final shift = running
                    ? targetEnd!.difference(step.end)
                    : Duration.zero;
                final shownStart = isCurrent && running
                    ? planned.start
                    : planned.start.add(shift);
                final shownEnd = isCurrent && running
                    ? targetEnd!
                    : planned.end.add(shift);
                final status = isDone
                    ? 'Rückgemeldet'
                    : isCurrent && running
                    ? 'Aktiv · ${hhmm(shownStart)}–${hhmm(shownEnd)}'
                    : isCurrent
                    ? 'Als Nächstes · startet erst nach Bestätigung'
                    : 'Voraussichtlich ${hhmm(shownStart)}–${hhmm(shownEnd)}';
                return ListTile(
                  leading: Icon(
                    isDone
                        ? Icons.check_circle
                        : isCurrent
                        ? Icons.play_circle_fill
                        : Icons.radio_button_unchecked,
                    color: isDone
                        ? const Color(0xff12b76a)
                        : isCurrent
                        ? const Color(0xff2563eb)
                        : const Color(0xff98a2b3),
                  ),
                  title: Text(
                    planned.item.name,
                    style: TextStyle(
                      fontWeight: isCurrent ? FontWeight.w800 : FontWeight.w600,
                    ),
                  ),
                  subtitle: Text(
                    '$status\n${planned.wholePieces} Stück · ${_number(planned.item.minutesPerPiece)} min/Stück',
                  ),
                  isThreeLine: true,
                  trailing: position > index
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              tooltip: 'Eine Position nach oben',
                              onPressed: position > index + 1
                                  ? () => moveUpcoming(position, position - 1)
                                  : null,
                              icon: const Icon(Icons.arrow_upward),
                            ),
                            IconButton(
                              tooltip: 'Eine Position nach unten',
                              onPressed: position < steps.length - 1
                                  ? () => moveUpcoming(position, position + 1)
                                  : null,
                              icon: const Icon(Icons.arrow_downward),
                            ),
                          ],
                        )
                      : null,
                );
              }),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    OutlinedButton.icon(
                      onPressed: addUpcoming,
                      icon: const Icon(Icons.add),
                      label: const Text('FOLGEAUFTRAG ANHÄNGEN'),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Folgeaufträge starten niemals automatisch.',
                      style: TextStyle(color: Color(0xff667085)),
                    ),
                  ],
                ),
              ),
            ],
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
            onPressed: reportAndFinish,
            icon: const Icon(Icons.check),
            label: const Text('ARBEIT RÜCKMELDEN'),
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
              onPressed: snoozeAlarm,
              icon: const Icon(Icons.snooze),
              label: Text(
                snoozeUntil != null
                    ? 'ERINNERUNG ${hhmm(snoozeUntil!)}'
                    : 'IN 5 MINUTEN ERNEUT ERINNERN',
              ),
            ),
          ],
        ],
      ],
    );
  }

  void start() {
    final current = DateTime.now();
    final step = steps[index];
    setState(() {
      startedAt = current;
      targetEnd = step.end;
      now = current;
      alarmed = false;
      snoozeUntil = null;
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
    final reminderDue = snoozeUntil == null || !now.isBefore(snoozeUntil!);
    if (!alarmed && reminderDue && !now.isBefore(targetEnd!)) {
      alarmed = true;
      snoozeUntil = null;
      SystemSound.play(SystemSoundType.alert);
      HapticFeedback.heavyImpact();
    }
  }

  Future<void> reportAndFinish() async {
    final step = steps[index];
    final draft = await showModalBottomSheet<_ReportDraft>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      isDismissible: false,
      enableDrag: false,
      builder: (context) => ReportSheet(
        step: step,
        startedAt: startedAt!,
        plannedEnd: targetEnd!,
      ),
    );
    if (draft == null || !mounted) return;
    final report = WorkReport(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      item: step.item,
      plannedPieces: step.wholePieces,
      actualPieces: draft.actualPieces,
      reportedPieces: draft.reportedPieces,
      startedAt: startedAt!,
      endedAt: draft.endedAt,
      plannedEnd: targetEnd!,
      plannedStart: step.start,
      completedOrder: draft.completedOrder,
      note: draft.note,
    );
    try {
      await widget.onReport(report);
      if (mounted) finish(draft.endedAt);
    } catch (exception) {
      if (!mounted) return;
      final message = exception
          .toString()
          .replaceFirst('Bad state: ', '')
          .replaceFirst('Exception: ', '');
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  void finish(DateTime reportedEnd) {
    timer?.cancel();
    AlarmService.instance.cancel();
    setState(() {
      _replanFutureFrom(reportedEnd);
      index++;
      startedAt = null;
      targetEnd = null;
      alarmed = false;
      snoozeUntil = null;
    });
    widget.onSessionChanged(index >= steps.length ? null : _snapshot());
  }

  void _replanFutureFrom(DateTime reportedEnd) {
    var cursor = reportedEnd;
    for (var position = index + 1; position < steps.length; position++) {
      final planned = steps[position];
      final end = addProductiveMinutes(
        cursor,
        planned.productiveSeconds / 60,
        planned.pauseStart,
        planned.pauseEnd,
      );
      steps[position] = planned.copyWith(start: cursor, end: end);
      cursor = end;
    }
  }

  void _replanUpcoming() {
    _replanFutureFrom(targetEnd ?? steps[index].end);
  }

  void moveUpcoming(int from, int to) {
    if (from <= index || to <= index || from == to) return;
    setState(() {
      final moved = steps.removeAt(from);
      steps.insert(to, moved);
      _replanUpcoming();
    });
    widget.onSessionChanged(_snapshot());
  }

  Future<void> addUpcoming() async {
    final item = await showModalBottomSheet<WorkItem>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) => const WorkItemSheet(),
    );
    if (item == null || !mounted) return;
    final previous = steps.last;
    final start = previous.end;
    final available = productiveMinutes(
      start,
      previous.capacityEnd,
      previous.pauseStart,
      previous.pauseEnd,
    );
    final capacityPieces = available / item.minutesPerPiece;
    final exactPieces = capacityPieces < item.quantity
        ? capacityPieces
        : item.quantity.toDouble();
    final lower = exactPieces.floor();
    final upper = exactPieces.ceil() > item.quantity
        ? item.quantity
        : exactPieces.ceil();
    final recommended = lower == upper || exactPieces - lower < 0.5
        ? lower
        : upper;
    final wholePieces = switch (item.roundingChoice) {
      RoundingChoice.down => lower,
      RoundingChoice.up => upper,
      RoundingChoice.automatic => recommended,
    };
    if (wholePieces <= 0) {
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Keine Schichtzeit mehr frei'),
          content: const Text(
            'Der Auftrag wurde nicht angehängt. Verlängere zuerst die Schichtplanung oder entferne eine zukünftige Arbeit.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      return;
    }
    final end = addProductiveMinutes(
      start,
      wholePieces * item.minutesPerPiece,
      previous.pauseStart,
      previous.pauseEnd,
    );
    setState(() {
      steps.add(
        ScheduleStep(
          item: item,
          start: start,
          end: end,
          pauseStart: previous.pauseStart,
          pauseEnd: previous.pauseEnd,
          capacityEnd: previous.capacityEnd,
          wholePieces: wholePieces,
          recommendedPieces: recommended,
          exactPieces: exactPieces,
        ),
      );
      _replanUpcoming();
    });
    widget.onSessionChanged(_snapshot());
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Folgeauftrag angehängt. Mit den Pfeilen kannst du ihn verschieben.',
        ),
      ),
    );
  }

  void snoozeAlarm() {
    AlarmService.instance.cancel();
    final reminder = DateTime.now().add(const Duration(minutes: 5));
    setState(() {
      alarmed = false;
      snoozeUntil = reminder;
    });
    AlarmService.instance.schedule(reminder, steps[index].item.name);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Arbeit läuft weiter – erneute Erinnerung um ${hhmm(reminder)}.',
        ),
      ),
    );
  }

  Future<void> extend() async {
    final previous = targetEnd!;
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
    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Soll-Ende wirklich ändern?'),
        content: Text(
          'Bisher: ${hhmm(previous)}\nNeu: ${hhmm(candidate)}\n\nCountdown, Alarm und die voraussichtlichen Folgezeiten werden angepasst.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('ABBRECHEN'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('ENDZEIT ÄNDERN'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() {
      targetEnd = candidate;
      alarmed = false;
    });
    widget.onSessionChanged(_snapshot());
    AlarmService.instance.schedule(candidate, steps[index].item.name);
  }

  WorkSessionSnapshot _snapshot() => WorkSessionSnapshot(
    steps: steps,
    index: index,
    startedAt: startedAt,
    targetEnd: targetEnd,
  );
}

class _ReportDraft {
  const _ReportDraft({
    required this.actualPieces,
    required this.reportedPieces,
    required this.endedAt,
    required this.completedOrder,
    required this.note,
  });

  final int actualPieces, reportedPieces;
  final DateTime endedAt;
  final bool completedOrder;
  final String note;
}

class ReportSheet extends StatefulWidget {
  const ReportSheet({
    super.key,
    required this.step,
    required this.startedAt,
    required this.plannedEnd,
  });

  final ScheduleStep step;
  final DateTime startedAt, plannedEnd;

  @override
  State<ReportSheet> createState() => _ReportSheetState();
}

class _ReportSheetState extends State<ReportSheet> {
  late final TextEditingController actualController;
  late final TextEditingController reportedController;
  final noteController = TextEditingController();
  late DateTime endedAt;
  bool completedOrder = false;
  String? error;

  DateTime get minuteNow => minutePrecision(DateTime.now());

  DateTime get earliestAllowed =>
      minuteNow.subtract(const Duration(minutes: 59));

  bool get planTimeAllowed {
    final plan = _minute(widget.plannedEnd);
    return !plan.isBefore(earliestAllowed) && !plan.isAfter(minuteNow);
  }

  DateTime _minute(DateTime value) => minutePrecision(value);

  @override
  void initState() {
    super.initState();
    actualController = TextEditingController(
      text: widget.step.item.isCredit ? '0' : '${widget.step.wholePieces}',
    );
    reportedController = TextEditingController(
      text: '${widget.step.wholePieces}',
    );
    endedAt = minuteNow;
  }

  @override
  void dispose() {
    actualController.dispose();
    reportedController.dispose();
    noteController.dispose();
    super.dispose();
  }

  Future<void> pickEndTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(endedAt),
    );
    if (picked == null) return;
    var candidate = DateTime(
      widget.startedAt.year,
      widget.startedAt.month,
      widget.startedAt.day,
      picked.hour,
      picked.minute,
    );
    if (candidate.isBefore(widget.startedAt) &&
        widget.startedAt.hour >= 12 &&
        picked.hour < 12) {
      candidate = candidate.add(const Duration(days: 1));
    }
    setState(() {
      endedAt = candidate;
      error = null;
    });
  }

  void save() {
    final actual = int.tryParse(actualController.text.trim());
    final reported = int.tryParse(reportedController.text.trim());
    if (actual == null || reported == null || actual < 0 || reported < 0) {
      setState(() => error = 'Bitte gültige, ganze Stückzahlen eingeben.');
      return;
    }
    final timeError = validateReportTime(
      now: DateTime.now(),
      startedAt: widget.startedAt,
      reportedAt: endedAt,
    );
    if (timeError != null) {
      setState(() => error = timeError);
      return;
    }
    Navigator.pop(
      context,
      _ReportDraft(
        actualPieces: actual,
        reportedPieces: reported,
        endedAt: endedAt,
        completedOrder: completedOrder,
        note: noteController.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.fromLTRB(
      20,
      16,
      20,
      20 + MediaQuery.viewInsetsOf(context).bottom,
    ),
    child: SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Arbeit rückmelden',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(widget.step.item.name),
          const SizedBox(height: 14),
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Text(
                'Geplant: ${widget.step.wholePieces} Stück · ${hhmm(widget.startedAt)}–${hhmm(widget.plannedEnd)}',
              ),
            ),
          ),
          const SizedBox(height: 14),
          if (widget.step.item.isCredit) ...[
            Card(
              margin: EdgeInsets.zero,
              child: const ListTile(
                leading: Icon(Icons.savings_outlined),
                title: Text('Guthaben abbauen'),
                subtitle: Text(
                  'Diese Stück wurden bereits körperlich bearbeitet.',
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: reportedController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Aus Guthaben rückmelden',
                suffixText: 'Stk',
              ),
            ),
          ] else
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: actualController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Tatsächlich bearbeitet',
                      suffixText: 'Stk',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: reportedController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Betrieblich rückgemeldet',
                      suffixText: 'Stk',
                    ),
                  ),
                ),
              ],
            ),
          const SizedBox(height: 10),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Abmeldezeit'),
            subtitle: Text(hhmm(endedAt)),
            trailing: const Icon(Icons.edit_outlined),
            onTap: pickEndTime,
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.tonalIcon(
                onPressed: () => setState(() {
                  endedAt = minuteNow;
                  error = null;
                }),
                icon: const Icon(Icons.schedule),
                label: const Text('JETZT'),
              ),
              FilledButton.tonalIcon(
                onPressed: planTimeAllowed
                    ? () => setState(() {
                        endedAt = _minute(widget.plannedEnd);
                        error = null;
                      })
                    : null,
                icon: const Icon(Icons.restart_alt),
                label: const Text('PLANZEIT'),
              ),
              OutlinedButton.icon(
                onPressed: pickEndTime,
                icon: const Icon(Icons.edit_outlined),
                label: const Text('ANDERE ZEIT'),
              ),
            ],
          ),
          if (!planTimeAllowed)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Planzeit liegt außerhalb des erlaubten Zeitfensters.',
                style: TextStyle(color: Color(0xff667085)),
              ),
            ),
          const SizedBox(height: 12),
          TextField(
            controller: noteController,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Notiz (optional)',
              hintText: 'Besonderheiten zu dieser Arbeit',
            ),
          ),
          const SizedBox(height: 8),
          if (!widget.step.item.isCredit)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: completedOrder,
              onChanged: (value) => setState(() => completedOrder = value),
              title: const Text('Gesamtauftrag vollständig beendet'),
              subtitle: Text(
                completedOrder
                    ? 'Der gesamte Auftrag wird als beendet vermerkt.'
                    : 'Teilrückmeldung – offene Stück bleiben bestehen.',
              ),
            ),
          if (error != null) ...[
            const SizedBox(height: 4),
            Text(error!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 12),
          FilledButton(
            onPressed: save,
            child: const Text('SPEICHERN UND ARBEIT BEENDEN'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('ABBRECHEN – ARBEIT WEITERLAUFEN LASSEN'),
          ),
        ],
      ),
    ),
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
  const MorePage({
    super.key,
    required this.reportCount,
    required this.creditCount,
    required this.onHistory,
    required this.onCredits,
    required this.onSettings,
  });
  final int reportCount, creditCount;
  final VoidCallback onHistory, onCredits, onSettings;

  @override
  Widget build(BuildContext context) => ResponsivePage(
    children: [
      const PageTitle(
        title: 'Mehr',
        subtitle: 'Daten und persönliche Einstellungen',
      ),
      const SizedBox(height: 16),
      Card(
        child: Column(
          children: [
            ListTile(
              leading: const Icon(Icons.savings_outlined),
              title: const Text('Guthaben'),
              subtitle: Text(
                creditCount == 1
                    ? '1 Auftrag mit verfügbarem Guthaben'
                    : '$creditCount Aufträge mit verfügbarem Guthaben',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: onCredits,
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.history),
              title: const Text('Meine Rückmeldungen'),
              subtitle: Text(
                reportCount == 1
                    ? '1 Rückmeldung lokal gespeichert'
                    : '$reportCount Rückmeldungen lokal gespeichert',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: onHistory,
            ),
            const Divider(height: 1),
            const ListTile(
              leading: Icon(Icons.precision_manufacturing_outlined),
              title: Text('Gesenkkatalog'),
              subtitle: Text('Folgt als eigener Bereich'),
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.settings_outlined),
              title: const Text('Einstellungen'),
              subtitle: const Text('Darstellung und App-Verhalten'),
              trailing: const Icon(Icons.chevron_right),
              onTap: onSettings,
            ),
          ],
        ),
      ),
    ],
  );
}

class CreditPage extends StatelessWidget {
  const CreditPage({super.key, required this.balances, required this.onPlan});
  final List<CreditBalance> balances;
  final void Function(CreditBalance, int) onPlan;

  Future<void> planCredit(BuildContext context, CreditBalance balance) async {
    final pieces = await showModalBottomSheet<int>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) => CreditUseSheet(balance: balance),
    );
    if (pieces != null && context.mounted) onPlan(balance, pieces);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Guthaben')),
    body: balances.isEmpty
        ? const Center(
            child: EmptyCard(
              icon: Icons.savings_outlined,
              text: 'Aktuell ist kein Guthaben verfügbar.',
            ),
          )
        : ResponsivePage(
            children: [
              const PageTitle(
                title: 'Mein Guthaben',
                subtitle: 'Bearbeitete, aber noch nicht gemeldete Stück',
              ),
              const SizedBox(height: 16),
              ...balances.map(
                (balance) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            balance.item.name,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${balance.producedPieces}/${balance.item.quantity} körperlich bearbeitet · ${balance.reportedPieces}/${balance.item.quantity} gemeldet',
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${balance.availablePieces} Stück Guthaben · ${_number(balance.availableMinutes)} Min.',
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.primary,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 14),
                          FilledButton.tonalIcon(
                            onPressed: () => planCredit(context, balance),
                            icon: const Icon(Icons.add_task),
                            label: const Text('IN DIE PLANUNG ÜBERNEHMEN'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
  );
}

class CreditUseSheet extends StatefulWidget {
  const CreditUseSheet({super.key, required this.balance});
  final CreditBalance balance;

  @override
  State<CreditUseSheet> createState() => _CreditUseSheetState();
}

class _CreditUseSheetState extends State<CreditUseSheet> {
  bool byMinutes = false;
  bool roundUp = true;
  late final TextEditingController controller;
  String? error;

  @override
  void initState() {
    super.initState();
    controller = TextEditingController(
      text: '${widget.balance.availablePieces}',
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  double? get entered =>
      double.tryParse(controller.text.trim().replaceAll(',', '.'));
  double get exactPieces =>
      (entered ?? 0) / widget.balance.item.minutesPerPiece;
  int get minutePieces => roundUp ? exactPieces.ceil() : exactPieces.floor();

  void changeMode(bool minutes) {
    setState(() {
      byMinutes = minutes;
      controller.text = minutes
          ? _number(widget.balance.availableMinutes)
          : '${widget.balance.availablePieces}';
      error = null;
    });
  }

  void submit() {
    final pieces = byMinutes ? minutePieces : entered?.toInt();
    if (entered == null || entered! <= 0 || pieces == null || pieces <= 0) {
      setState(() => error = 'Bitte eine gültige Menge eingeben.');
      return;
    }
    if (!byMinutes && entered! != pieces) {
      setState(() => error = 'Stückzahl bitte ohne Dezimalstellen eingeben.');
      return;
    }
    if (pieces > widget.balance.availablePieces) {
      setState(
        () => error =
            'Es sind nur ${widget.balance.availablePieces} Stück Guthaben verfügbar.',
      );
      return;
    }
    Navigator.pop(context, pieces);
  }

  @override
  Widget build(BuildContext context) {
    final lower = exactPieces.floor();
    final upper = exactPieces.ceil();
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        18,
        20,
        20 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Guthaben einplanen',
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(widget.balance.item.name),
            const SizedBox(height: 16),
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: false, label: Text('Stück')),
                ButtonSegment(value: true, label: Text('Minuten')),
              ],
              selected: {byMinutes},
              onSelectionChanged: (value) => changeMode(value.single),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: controller,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              onChanged: (_) => setState(() => error = null),
              decoration: InputDecoration(
                labelText: byMinutes ? 'Gewünschte Minuten' : 'Stückzahl',
                suffixText: byMinutes ? 'Min.' : 'Stk',
              ),
            ),
            if (byMinutes && entered != null && entered! > 0) ...[
              const SizedBox(height: 10),
              Text('${_number(exactPieces)} Stück rechnerisch'),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    selected: !roundUp,
                    onSelected: (_) => setState(() => roundUp = false),
                    label: Text('$lower Stück abrunden'),
                  ),
                  ChoiceChip(
                    selected: roundUp,
                    onSelected: (_) => setState(() => roundUp = true),
                    label: Text('$upper Stück aufrunden'),
                  ),
                ],
              ),
            ],
            if (error != null) ...[
              const SizedBox(height: 8),
              Text(
                error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 18),
            FilledButton(
              onPressed: submit,
              child: const Text('ZUR PLANUNG HINZUFÜGEN'),
            ),
          ],
        ),
      ),
    );
  }
}

class SettingsPage extends StatefulWidget {
  const SettingsPage({
    super.key,
    required this.themeMode,
    required this.onThemeChanged,
  });
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode> onThemeChanged;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late ThemeMode current;

  @override
  void initState() {
    super.initState();
    current = widget.themeMode;
  }

  void select(ThemeMode value) {
    setState(() => current = value);
    widget.onThemeChanged(value);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Einstellungen')),
    body: ResponsivePage(
      children: [
        const PageTitle(
          title: 'Darstellung',
          subtitle: 'WerkMate an dein Gerät anpassen',
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SegmentedButton<ThemeMode>(
                  segments: const [
                    ButtonSegment(
                      value: ThemeMode.system,
                      icon: Icon(Icons.brightness_auto_outlined),
                      label: Text('System'),
                    ),
                    ButtonSegment(
                      value: ThemeMode.light,
                      icon: Icon(Icons.light_mode_outlined),
                      label: Text('Hell'),
                    ),
                    ButtonSegment(
                      value: ThemeMode.dark,
                      icon: Icon(Icons.dark_mode_outlined),
                      label: Text('Dunkel'),
                    ),
                  ],
                  selected: {current},
                  onSelectionChanged: (value) => select(value.single),
                ),
                const SizedBox(height: 12),
                Text(
                  current == ThemeMode.system
                      ? 'WerkMate folgt automatisch deinem Smartphone.'
                      : current == ThemeMode.dark
                      ? 'Dunkle Darstellung ist dauerhaft aktiv.'
                      : 'Helle Darstellung ist dauerhaft aktiv.',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'Weitere Einstellungen kommen nur hinzu, wenn sie den Arbeitsablauf wirklich vereinfachen.',
          style: TextStyle(color: Color(0xff667085)),
        ),
      ],
    ),
  );
}

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  final store = ReportStore();
  List<WorkReport>? reports;

  @override
  void initState() {
    super.initState();
    reload();
  }

  Future<void> reload() async {
    final value = await store.load();
    value.sort((a, b) => b.endedAt.compareTo(a.endedAt));
    if (mounted) setState(() => reports = value);
  }

  Future<void> deleteReport(WorkReport report) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rückmeldung löschen?'),
        content: Text(
          '${report.item.name}\n${_date(report.endedAt)} · ${hhmm(report.startedAt)}–${hhmm(report.endedAt)}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('ABBRECHEN'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('LÖSCHEN'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await store.delete(report.id);
    await reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Meine Rückmeldungen')),
    body: reports == null
        ? const Center(child: CircularProgressIndicator())
        : reports!.isEmpty
        ? const Center(
            child: EmptyCard(
              icon: Icons.history,
              text: 'Noch keine Arbeiten rückgemeldet.',
            ),
          )
        : ResponsivePage(
            children: [
              PageTitle(
                title: 'Historie',
                subtitle: '${reports!.length} lokal gespeicherte Rückmeldungen',
              ),
              const SizedBox(height: 16),
              ...reports!.map(
                (report) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: ReportHistoryCard(
                    report: report,
                    onDelete: () => deleteReport(report),
                  ),
                ),
              ),
            ],
          ),
  );
}

class ReportHistoryCard extends StatelessWidget {
  const ReportHistoryCard({
    super.key,
    required this.report,
    required this.onDelete,
  });
  final WorkReport report;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final time = report.timeDeviationMinutes;
    final pieces = report.pieceDeviation;
    final timePercent = report.plannedMinutes == 0
        ? 0.0
        : time / report.plannedMinutes * 100;
    return Card(
      child: ExpansionTile(
        tilePadding: const EdgeInsets.fromLTRB(18, 8, 10, 8),
        childrenPadding: const EdgeInsets.fromLTRB(18, 0, 18, 16),
        title: Text(
          report.item.name,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          report.item.isCredit
              ? '${_date(report.endedAt)} · ${hhmm(report.startedAt)}–${hhmm(report.endedAt)}\n${report.reportedPieces} Stück aus Guthaben gemeldet'
              : '${_date(report.endedAt)} · ${hhmm(report.startedAt)}–${hhmm(report.endedAt)}\n${report.actualPieces} bearbeitet · ${report.reportedPieces} gemeldet',
        ),
        children: [
          const Divider(),
          _DeviationRow(
            icon: Icons.schedule,
            label: time > 0
                ? '${_number(time.abs())} Min. Verzug (${_signedPercent(timePercent)})'
                : time < 0
                ? '${_number(time.abs())} Min. früher (${_signedPercent(timePercent)})'
                : 'Zeit genau eingehalten',
            color: time > 0
                ? const Color(0xffb42318)
                : time < 0
                ? const Color(0xff067647)
                : const Color(0xff667085),
          ),
          if (report.item.isCredit)
            _DeviationRow(
              icon: Icons.savings_outlined,
              label: '${report.reportedPieces} Stück Guthaben verwendet',
              color: const Color(0xff2563eb),
            )
          else
            _DeviationRow(
              icon: Icons.inventory_2_outlined,
              label: pieces > 0
                  ? '+$pieces Stück mehr als geplant'
                  : pieces < 0
                  ? '${pieces.abs()} Stück weniger als geplant'
                  : 'Stückzahl genau eingehalten',
              color: pieces > 0
                  ? const Color(0xff067647)
                  : pieces < 0
                  ? const Color(0xffb42318)
                  : const Color(0xff667085),
            ),
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              report.item.isCredit
                  ? 'Guthabenrückmeldung'
                  : report.completedOrder
                  ? 'Gesamtauftrag vollständig beendet'
                  : 'Teilrückmeldung',
            ),
          ),
          if (report.note.isNotEmpty) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Text('Notiz: ${report.note}'),
            ),
          ],
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: onDelete,
              icon: const Icon(Icons.delete_outline),
              label: const Text('LÖSCHEN'),
            ),
          ),
        ],
      ),
    );
  }
}

class _DeviationRow extends StatelessWidget {
  const _DeviationRow({
    required this.icon,
    required this.label,
    required this.color,
  });
  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      children: [
        Icon(icon, color: color),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            label,
            style: TextStyle(color: color, fontWeight: FontWeight.w700),
          ),
        ),
      ],
    ),
  );
}

String _date(DateTime value) =>
    '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')}.${value.year}';

String _signedPercent(double value) =>
    '${value >= 0 ? '+' : '−'}${value.abs().toStringAsFixed(1).replaceAll('.', ',')} %';

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
