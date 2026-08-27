"""Einfache grafische PC-Oberfläche für den WerkMate-MVP."""

from __future__ import annotations

import json
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import __version__
from .cli import default_database_path, format_duration, parse_datetime, warn_unusual_end
from .database import WerkMateDatabase
from .performance import (
    calculate_performance,
    format_quantity_performance,
    format_time_performance,
)
from .service import WerkMateService, with_custom_shift_end
from .timecalc import minutes_to_seconds, productive_duration_between, seconds_to_minutes


def local_now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def display_time(value: str | None) -> str:
    if not value:
        return "–"
    return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")


def format_piece_equivalent(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)).replace(".", ",")


def format_total_target_time(seconds: int) -> str:
    total_minutes = Decimal(seconds) / Decimal(60)
    minute_text = str(total_minutes.quantize(Decimal("0.1"))).replace(".", ",")
    hours, remainder = divmod(int(seconds), 3_600)
    minutes = remainder // 60
    return f"{minute_text} min ({hours} h {minutes:02d} min)"


def parse_plan_start_override(value: str, plan_start: datetime) -> datetime:
    """Accept a full timestamp or a convenient HH:MM value for the plan."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Die Startzeit darf nicht leer sein.")
    try:
        clock = datetime.strptime(cleaned, "%H:%M").time()
    except ValueError:
        return parse_datetime(cleaned)
    result = datetime.combine(plan_start.date(), clock)
    if result < plan_start:
        result += timedelta(days=1)
    return result


def parse_plan_start(value: str, today: date | None = None) -> datetime:
    """Parse the plan's start; HH:MM means that clock time on the current day."""
    cleaned = value.strip()
    try:
        clock = datetime.strptime(cleaned, "%H:%M").time()
    except ValueError:
        return parse_datetime(cleaned)
    return datetime.combine(today or local_now().date(), clock)


def current_shift_number(at: datetime, settings: list[dict] | None = None) -> int:
    if settings:
        current = at.time()
        for item in settings:
            start = datetime.strptime(item["start_time"], "%H:%M").time()
            end = datetime.strptime(item["end_time"], "%H:%M").time()
            inside = start <= current < end if start < end else current >= start or current < end
            if inside:
                return int(item["shift_number"])
    current = at.time()
    if current >= datetime.strptime("05:45", "%H:%M").time() and current < datetime.strptime("13:45", "%H:%M").time():
        return 1
    if current >= datetime.strptime("13:45", "%H:%M").time() and current < datetime.strptime("21:45", "%H:%M").time():
        return 2
    return 3


class WerkMateApp(tk.Tk):
    def __init__(self, database_path=None) -> None:
        super().__init__()
        self.title(f"WerkMate {__version__}")
        self.geometry("980x700")
        self.minsize(840, 600)

        self.database = WerkMateDatabase(database_path or default_database_path())
        self.service = WerkMateService(self.database)
        self.notified_session_id: int | None = None

        self._configure_style()
        self._build_ui()
        self.load_persisted_shift_plan()
        self.refresh_all()
        self.after(1_000, self._tick)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Countdown.TLabel", font=("Segoe UI", 34, "bold"))
        style.configure("Danger.TLabel", font=("Segoe UI", 34, "bold"), foreground="#b42318")
        style.configure("Muted.TLabel", foreground="#667085")
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=8)

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(18, 14))
        header.pack(fill="x")
        ttk.Label(header, text="WerkMate", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text=f"lokal · Version {__version__}",
            style="Muted.TLabel",
        ).pack(side="right")
        ttk.Button(header, text="Daten sichern", command=self.backup_database).pack(
            side="right", padx=(0, 14)
        )

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.dashboard_tab = ttk.Frame(self.tabs, padding=18)
        self.quick_tab = ttk.Frame(self.tabs, padding=18)
        self.analytics_tab = ttk.Frame(self.tabs, padding=18)
        self.plan_tab = ttk.Frame(self.tabs, padding=18)
        self.orders_tab = ttk.Frame(self.tabs, padding=18)
        self.catalog_tab = ttk.Frame(self.tabs, padding=18)
        self.history_tab = ttk.Frame(self.tabs, padding=18)
        self.settings_tab = ttk.Frame(self.tabs, padding=18)
        self.tabs.add(self.dashboard_tab, text="Laufender Auftrag")
        self.tabs.add(self.analytics_tab, text="Auswertung")
        self.tabs.add(self.quick_tab, text="Schnellstart")
        self.tabs.add(self.plan_tab, text="Schichtplan")
        self.tabs.add(self.orders_tab, text="Aufträge")
        self.tabs.add(self.catalog_tab, text="Gesenk-Katalog")
        self.tabs.add(self.history_tab, text="Historie")
        self.tabs.add(self.settings_tab, text="Einstellungen")

        self._build_dashboard()
        self._build_analytics()
        self._build_quick_start()
        self._build_shift_plan()
        self._build_orders()
        self._build_catalog()
        self._build_history()
        self._build_settings()

    def _current_shift_number(self, at: datetime) -> int:
        return current_shift_number(at, self.database.shift_settings())

    def _build_dashboard(self) -> None:
        self.active_title = ttk.Label(
            self.dashboard_tab, text="Kein laufender Auftrag", style="Title.TLabel"
        )
        self.active_title.pack(anchor="w")
        self.active_details = ttk.Label(self.dashboard_tab, text="", style="Muted.TLabel")
        self.active_details.pack(anchor="w", pady=(4, 24))
        self.countdown_caption = ttk.Label(self.dashboard_tab, text="")
        self.countdown_caption.pack()
        self.countdown = ttk.Label(self.dashboard_tab, text="--:--:--", style="Countdown.TLabel")
        self.countdown.pack(pady=(4, 18))
        self.work_progress = ttk.Progressbar(self.dashboard_tab, maximum=100, mode="determinate")
        self.work_progress.pack(fill="x", padx=80, pady=(0, 10))
        self.target_label = ttk.Label(self.dashboard_tab, text="")
        self.target_label.pack()
        self.extend_work_button = ttk.Button(
            self.dashboard_tab, text="Brauche länger / neue Endzeit setzen",
            command=self.extend_active_session,
        )
        self.extend_work_button.pack(pady=(8, 0))
        self.forecast_label = ttk.Label(self.dashboard_tab, text="", justify="center")
        self.forecast_label.pack(pady=18)
        self.order_remaining_label = ttk.Label(
            self.dashboard_tab, text="", justify="center", style="Muted.TLabel"
        )
        self.order_remaining_label.pack(pady=(0, 8))
        self.cancel_work_button = ttk.Button(
            self.dashboard_tab,
            text="Fehlstart / Arbeitseinsatz abbrechen",
            command=self.cancel_active,
        )
        self.cancel_work_button.pack()

        finish = ttk.LabelFrame(self.dashboard_tab, text="Arbeitseinsatz rückmelden", padding=14)
        finish.pack(fill="x", pady=(20, 0))
        self.finish_actual_label = ttk.Label(finish, text="Tatsächlich bearbeitet:")
        self.finish_actual_label.grid(row=0, column=0, sticky="w")
        self.finish_quantity = ttk.Entry(finish, width=10)
        self.finish_quantity.grid(row=0, column=1, padx=(8, 18), sticky="w")
        self.finish_reported_label = ttk.Label(finish, text="Betrieblich rückgemeldet:")
        self.finish_reported_label.grid(row=0, column=2, sticky="w")
        self.finish_reported_quantity = ttk.Entry(finish, width=10)
        self.finish_reported_quantity.grid(row=0, column=3, padx=(8, 18), sticky="w")
        ttk.Label(finish, text="Abmeldezeit:").grid(row=0, column=4, sticky="w")
        self.finish_time = ttk.Entry(finish, width=19)
        self.finish_time.grid(row=0, column=5, padx=8, sticky="w")
        ttk.Button(finish, text="Aktuelle Zeit", command=self._fill_finish_now).grid(row=0, column=6)
        ttk.Label(finish, text="Notiz:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.finish_note = ttk.Entry(finish)
        self.finish_note.grid(row=1, column=1, columnspan=6, sticky="ew", padx=(8, 0), pady=(12, 0))
        self.partial_finish_button = ttk.Button(
            finish, text="Teilrückmelden / Arbeitseinsatz unterbrechen", style="Primary.TButton",
            command=self.finish_active,
        )
        self.partial_finish_button.grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=(16, 0), padx=(0, 6)
        )
        self.finish_entire_button = ttk.Button(
            finish,
            text="Gesamtauftrag vollständig beenden",
            style="Primary.TButton",
            command=self.finish_entire_order,
        )
        self.finish_entire_button.grid(
            row=2, column=4, columnspan=3, sticky="ew", pady=(16, 0), padx=(6, 0)
        )
        finish.columnconfigure(5, weight=1)

    def _build_analytics(self) -> None:
        header = ttk.Frame(self.analytics_tab)
        header.pack(fill="x")
        ttk.Label(header, text="Persönliche Auswertung", style="Title.TLabel").pack(side="left")
        self.analytics_period = ttk.Combobox(
            header, values=("Heute", "Diese Woche"), state="readonly", width=16
        )
        self.analytics_period.set("Heute")
        self.analytics_period.pack(side="right")
        self.analytics_period.bind("<<ComboboxSelected>>", lambda _event: self.refresh_analytics())
        cards = ttk.LabelFrame(self.analytics_tab, text="Zusammenfassung", padding=14)
        cards.pack(fill="x", pady=(16, 12))
        self.analytics_labels = []
        for column, caption in enumerate(
            ("Einsätze", "Bearbeitet", "Rückgemeldet", "Guthabenänderung", "Zeit", "Stück")
        ):
            cell = ttk.Frame(cards)
            cell.grid(row=0, column=column, sticky="nsew", padx=8)
            ttk.Label(cell, text=caption, style="Muted.TLabel").pack()
            value = ttk.Label(cell, text="–", font=("Segoe UI", 13, "bold"))
            value.pack(pady=(4, 0))
            self.analytics_labels.append(value)
            cards.columnconfigure(column, weight=1)
        table = ttk.LabelFrame(self.analytics_tab, text="Tageswerte", padding=10)
        table.pack(fill="both", expand=True)
        columns = ("date", "sessions", "actual", "reported", "credit", "time", "pieces")
        self.analytics_tree = ttk.Treeview(table, columns=columns, show="headings", height=14)
        for column, heading, width in zip(
            columns,
            ("Datum", "Einsätze", "Bearbeitet", "Rückgemeldet", "Guthaben", "Zeitabweichung", "Stückabweichung"),
            (100, 80, 100, 110, 100, 180, 180),
        ):
            self.analytics_tree.heading(column, text=heading)
            self.analytics_tree.column(column, width=width, anchor="center")
        self.analytics_tree.pack(fill="both", expand=True)
        ttk.Label(
            self.analytics_tab,
            text="Grün = früher bzw. mehr als geplant · Rot = später bzw. weniger als geplant",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(8, 0))

    @staticmethod
    def _analytics_delta(actual: int, planned: int, *, seconds: bool = False) -> str:
        delta = actual - planned
        percent = delta / planned * 100 if planned else 0
        if seconds:
            value = f"{abs(delta) // 60} min"
            good = delta <= 0
            wording = "früher" if delta < 0 else "später" if delta > 0 else "genau"
        else:
            value = f"{abs(delta)} Stk"
            good = delta >= 0
            wording = "mehr" if delta > 0 else "weniger" if delta < 0 else "genau"
        color = "🟢" if good else "🔴"
        return f"{color} {value} {wording} ({abs(percent):.1f} %)" if delta else f"🟢 {wording}"

    def refresh_analytics(self) -> None:
        today = date.today()
        start = today if self.analytics_period.get() == "Heute" else today - timedelta(days=today.weekday())
        result = self.service.statistics(start, today)
        total = result["total"]
        time_text = self._analytics_delta(total["actual_seconds"], total["planned_seconds"], seconds=True)
        piece_text = self._analytics_delta(total["measured_quantity"], total["planned_quantity"])
        values = (
            total["sessions"], total["completed"], total["reported"],
            f"{total['credit_change']:+d} Stk", time_text, piece_text,
        )
        for label, value in zip(self.analytics_labels, values):
            label.configure(text=value)
        self.analytics_tree.delete(*self.analytics_tree.get_children())
        for item in result["days"]:
            self.analytics_tree.insert("", "end", values=(
                item["date"].strftime("%d.%m.%Y"), item["sessions"], item["completed"],
                item["reported"], f"{item['credit_change']:+d}",
                self._analytics_delta(item["actual_seconds"], item["planned_seconds"], seconds=True),
                self._analytics_delta(item["measured_quantity"], item["planned_quantity"]),
            ))

    def _build_orders(self) -> None:
        form = ttk.LabelFrame(self.orders_tab, text="Neuen Auftrag anlegen", padding=12)
        form.pack(fill="x")
        labels = ("Auftragsnummer", "Gesenknummer", "Arbeitsgang", "Menge", "min/Stück")
        self.order_entries: list[ttk.Entry] = []
        for column, label in enumerate(labels):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=4)
            entry = ttk.Combobox(form, width=16) if column in (1, 2) else ttk.Entry(form, width=16)
            entry.grid(row=1, column=column, sticky="ew", padx=4, pady=(3, 8))
            self.order_entries.append(entry)
            form.columnconfigure(column, weight=1)
        ttk.Label(form, text="Auftragsnotiz").grid(row=2, column=0, sticky="w", padx=4)
        self.order_note = ttk.Entry(form)
        self.order_note.grid(row=3, column=0, columnspan=4, sticky="ew", padx=4)
        ttk.Button(form, text="Auftrag anlegen", command=self.create_order).grid(
            row=3, column=4, sticky="ew", padx=4
        )
        self.order_total_time = ttk.Label(form, text="Gesamtvorgabezeit: –", style="Muted.TLabel")
        self.order_total_time.grid(row=4, column=0, columnspan=5, sticky="w", padx=4, pady=(8, 0))
        self.order_entries[3].bind("<KeyRelease>", lambda _event: self.refresh_order_total_time())
        self.order_entries[4].bind("<KeyRelease>", lambda _event: self.refresh_order_total_time())

        list_frame = ttk.LabelFrame(self.orders_tab, text="Gespeicherte Aufträge", padding=10)
        list_frame.pack(fill="both", expand=True, pady=14)
        columns = (
            "id", "order", "die", "operation", "processed", "reported",
            "credit", "open", "time", "status",
        )
        self.orders_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        headings = (
            "ID", "Auftrag", "Gesenk", "AG", "Bearbeitet", "Rückgemeldet",
            "Guthaben", "Noch bearbeiten", "Gesamtzeit", "Status"
        )
        widths = (40, 105, 75, 55, 90, 95, 170, 95, 155, 125)
        for column, heading, width in zip(columns, headings, widths):
            self.orders_tree.heading(column, text=heading)
            self.orders_tree.column(column, width=width, anchor="center")
        self.orders_tree.pack(fill="both", expand=True)
        self.orders_tree.bind("<Double-1>", lambda _event: self.edit_selected_order())
        self.orders_tree.bind("<<TreeviewSelect>>", self._order_selected)
        order_actions = ttk.Frame(list_frame)
        order_actions.pack(fill="x", pady=(8, 0))
        ttk.Button(order_actions, text="Auftrag bearbeiten", command=self.edit_selected_order).pack(
            side="left"
        )
        ttk.Button(order_actions, text="Änderungen anzeigen", command=self.show_order_corrections).pack(
            side="left", padx=8
        )
        ttk.Button(order_actions, text="Guthaben anmelden", command=self.open_credit_dialog).pack(
            side="left"
        )
        ttk.Button(order_actions, text="Duplizieren", command=self.duplicate_selected_order).pack(
            side="left", padx=8
        )
        ttk.Button(order_actions, text="In Papierkorb", command=self.archive_selected_order).pack(
            side="left"
        )
        ttk.Button(order_actions, text="Papierkorb", command=self.open_order_trash).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(order_actions, text="Abgegebenen Auftrag wieder aufnehmen", command=self.resume_selected).pack(
            side="right"
        )

        start = ttk.LabelFrame(self.orders_tab, text="Ausgewählten Auftrag starten", padding=12)
        start.pack(fill="x")
        ttk.Label(start, text="Menge:").grid(row=0, column=0, sticky="w")
        self.start_quantity = ttk.Entry(start, width=9)
        self.start_quantity.grid(row=0, column=1, padx=(6, 18))
        ttk.Label(start, text="Anmeldezeit:").grid(row=0, column=2, sticky="w")
        self.start_time = ttk.Entry(start, width=19)
        self.start_time.grid(row=0, column=3, padx=6)
        ttk.Button(start, text="Jetzt", command=self._fill_start_now).grid(row=0, column=4, padx=(0, 18))
        ttk.Label(start, text="Schicht:").grid(row=0, column=5)
        self.shift_number = ttk.Combobox(start, values=("1", "2", "3"), width=5, state="readonly")
        self.shift_number.grid(row=0, column=6, padx=6)
        ttk.Button(
            start, text="Arbeit starten", style="Primary.TButton", command=self.start_selected
        ).grid(row=0, column=7, sticky="ew")
        ttk.Button(start, text="Rest abgeben", command=self.hand_off_selected).grid(
            row=1, column=7, sticky="ew", pady=(8, 0)
        )
        self.start_forecast = ttk.Label(
            start,
            text="Auftrag und Schicht auswählen, um die Sollstückzahl zu berechnen.",
            justify="left",
        )
        self.start_forecast.grid(row=1, column=0, columnspan=7, sticky="w", pady=(10, 0))
        start.columnconfigure(7, weight=1)
        self.order_entries[1].bind("<<ComboboxSelected>>", self._catalog_die_selected)
        self.order_entries[1].bind("<FocusIn>", lambda _event: self._refresh_die_suggestions())
        self.order_entries[2].bind("<<ComboboxSelected>>", self._catalog_operation_selected)
        self.start_time.bind(
            "<FocusOut>", lambda _event: self.refresh_start_forecast(apply_recommendation=True)
        )
        self.shift_number.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh_start_forecast(apply_recommendation=True),
        )
        self.shift_number.set(str(self._current_shift_number(local_now())))
        self._fill_start_now()

    def _build_quick_start(self) -> None:
        ttk.Label(self.quick_tab, text="Mit möglichst wenigen Angaben starten", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            self.quick_tab,
            text="Pflicht ist nur die Gesamtmenge plus entweder eine Stückzeit oder eine bekannte Gesenknummer.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 18))
        form = ttk.LabelFrame(self.quick_tab, text="Schnellauftrag", padding=18)
        form.pack(fill="x")

        labels = (
            "Gesamtmenge *", "Stückzeit min", "Gesenknummer", "Arbeitsgang",
            "Auftragsnummer (optional)", "Anmeldezeit", "Schicht",
        )
        self.quick_entries: list[ttk.Entry] = []
        for index, label in enumerate(labels):
            row = (index // 4) * 2
            column = index % 4
            ttk.Label(form, text=label).grid(row=row, column=column, sticky="w", padx=6)
            if index in (2, 3):
                entry = ttk.Combobox(form, width=22)
            elif index == 6:
                entry = ttk.Combobox(form, values=("1", "2", "3"), state="readonly", width=22)
            else:
                entry = ttk.Entry(form, width=24)
            entry.grid(row=row + 1, column=column, sticky="ew", padx=6, pady=(3, 14))
            self.quick_entries.append(entry)
            form.columnconfigure(column, weight=1)

        self.quick_entries[2].bind("<FocusIn>", lambda _event: self._refresh_quick_dies())
        self.quick_entries[2].bind("<<ComboboxSelected>>", self._quick_die_selected)
        self.quick_entries[6].set(str(self._current_shift_number(local_now())))
        self._set_entry(self.quick_entries[5], local_now().strftime("%Y-%m-%d %H:%M"))
        ttk.Label(form, text="Notiz (optional)").grid(row=4, column=0, sticky="w", padx=6)
        self.quick_note = ttk.Entry(form)
        self.quick_note.grid(row=5, column=0, columnspan=3, sticky="ew", padx=6)
        ttk.Button(
            form,
            text="JETZT STARTEN",
            style="Primary.TButton",
            command=self.quick_start,
        ).grid(row=5, column=3, sticky="ew", padx=6)

        examples = ttk.LabelFrame(self.quick_tab, text="Mögliche Eingabekombinationen", padding=14)
        examples.pack(fill="x", pady=18)
        ttk.Label(
            examples,
            text=(
                "• Menge + Stückzeit\n"
                "• Menge + Gesenknummer (wenn genau ein Arbeitsgang hinterlegt ist)\n"
                "• Menge + Gesenknummer + Arbeitsgang\n"
                "• Optional zusätzlich eine echte Auftragsnummer und Notiz\n\n"
                "Anmeldezeit und aktuelle Schicht sind bereits vorausgefüllt. WerkMate erstellt den Auftrag, "
                "berechnet die sinnvolle Schichtmenge und startet den persönlichen Einsatz."
            ),
            justify="left",
        ).pack(anchor="w")

    def _build_shift_plan(self) -> None:
        self.shift_plan_items: list[dict] = []
        self.shift_plan_results: list[dict] = []
        self._plan_date = local_now().date()
        ttk.Label(self.plan_tab, text="Aufträge und Guthaben zusammen planen", style="Title.TLabel").pack(
            anchor="w"
        )
        settings = ttk.Frame(self.plan_tab)
        settings.pack(fill="x", pady=(12, 8))
        ttk.Label(settings, text="Planstart (Uhrzeit):").pack(side="left")
        self.plan_start = ttk.Entry(settings, width=20)
        self.plan_start.insert(0, local_now().strftime("%H:%M"))
        self.plan_start.pack(side="left", padx=(6, 16))
        ttk.Label(settings, text="Schicht:").pack(side="left")
        self.plan_shift = ttk.Combobox(settings, values=("1", "2", "3"), state="readonly", width=6)
        self.plan_shift.set(str(self._current_shift_number(local_now())))
        self.plan_shift.pack(side="left", padx=6)
        ttk.Label(settings, text="Heutiges Schichtende (optional):").pack(side="left", padx=(14, 0))
        self.plan_custom_end = ttk.Entry(settings, width=8)
        self.plan_custom_end.pack(side="left", padx=6)
        ttk.Label(settings, text="leer = normale Schicht", style="Muted.TLabel").pack(side="left")
        ttk.Label(
            self.plan_tab,
            text=(
                "Der Planstart gilt für den ersten Auftrag. Alle weiteren Startzeiten werden "
                "automatisch aus dem Ende des vorherigen Auftrags berechnet."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        add = ttk.LabelFrame(self.plan_tab, text="Planpunkt hinzufügen", padding=10)
        add.pack(fill="x")
        ttk.Label(add, text="Auftrag:").grid(row=0, column=0, sticky="w")
        self.plan_order = ttk.Combobox(add, state="readonly", width=42)
        self.plan_order.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.plan_order.bind("<FocusIn>", lambda _event: self.refresh_plan_orders())
        ttk.Label(add, text="Art:").grid(row=0, column=1, sticky="w")
        self.plan_mode = ttk.Combobox(
            add,
            values=(
                "Bis Schichtende begrenzen",
                "Feste Stückzahl (Überzeit möglich)",
                "Restschicht mit Auftrag füllen",
                "Guthaben nach Stück",
                "Guthaben nach Minuten",
            ),
            state="readonly",
            width=30,
        )
        self.plan_mode.set("Bis Schichtende begrenzen")
        self.plan_mode.grid(row=1, column=1, sticky="ew", padx=8)
        self.plan_value_label = ttk.Label(add, text="Maximale Stückzahl (leer = alle offenen):")
        self.plan_value_label.grid(row=0, column=2, sticky="w")
        self.plan_value = ttk.Entry(add, width=15)
        self.plan_value.grid(row=1, column=2, sticky="ew", padx=8)
        self.plan_mode.bind("<<ComboboxSelected>>", self._update_plan_value_label)
        ttk.Button(add, text="Zum Plan hinzufügen", command=self.add_shift_plan_item).grid(
            row=1, column=3, sticky="ew", padx=(8, 0)
        )
        ttk.Button(
            add, text="Manuellen Auftrag eintragen", command=self.add_manual_shift_plan_item
        ).grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        add.columnconfigure(0, weight=2)
        add.columnconfigure(1, weight=1)

        queue_frame = ttk.LabelFrame(self.plan_tab, text="Reihenfolge", padding=8)
        queue_frame.pack(fill="x", pady=10)
        self.plan_queue = ttk.Treeview(
            queue_frame,
            columns=("pos", "order", "die", "mode", "value", "start"),
            show="headings",
            height=5,
        )
        for column, heading, width in zip(
            ("pos", "order", "die", "mode", "value", "start"),
            ("Pos.", "Auftrag", "Gesenk/AG", "Planungsart", "Vorgabe", "Startvorgabe"),
            (45, 150, 130, 230, 110, 130),
        ):
            self.plan_queue.heading(column, text=heading)
            self.plan_queue.column(column, width=width, anchor="center")
        self.plan_queue.pack(fill="x")
        self._plan_drag_source: int | None = None
        self.plan_queue.bind("<ButtonPress-1>", self._plan_drag_start)
        self.plan_queue.bind("<ButtonRelease-1>", self._plan_drag_release)
        queue_buttons = ttk.Frame(queue_frame)
        queue_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(queue_buttons, text="Ausgewählten entfernen", command=self.remove_shift_plan_item).pack(
            side="left"
        )
        ttk.Button(
            queue_buttons, text="Startzeit bearbeiten", command=self.edit_plan_item_start
        ).pack(side="left", padx=6)
        ttk.Button(
            queue_buttons, text="Planpunkt bearbeiten", command=self.edit_shift_plan_item
        ).pack(side="left", padx=(0, 6))
        ttk.Button(queue_buttons, text="▲", width=4, command=lambda: self.move_plan_item(-1)).pack(
            side="left"
        )
        ttk.Button(queue_buttons, text="▼", width=4, command=lambda: self.move_plan_item(1)).pack(
            side="left", padx=(3, 6)
        )
        ttk.Button(queue_buttons, text="Plan leeren", command=self.clear_shift_plan).pack(
            side="left", padx=6
        )
        self.plan_saved_label = ttk.Label(queue_buttons, text="", style="Muted.TLabel")
        self.plan_saved_label.pack(side="left", padx=8)
        ttk.Button(
            queue_buttons, text="SCHICHT BERECHNEN", style="Primary.TButton",
            command=self.calculate_shift_plan,
        ).pack(side="right")

        result_frame = ttk.LabelFrame(self.plan_tab, text="Berechneter Ablauf", padding=8)
        result_frame.pack(fill="both", expand=True)
        self.plan_total_label = ttk.Label(
            result_frame, text="Gesamtzeit: –", font=("Segoe UI", 12, "bold")
        )
        self.plan_total_label.pack(anchor="w", pady=(0, 8))
        self.plan_capacity_bar = ttk.Progressbar(result_frame, maximum=100, mode="determinate")
        self.plan_capacity_bar.pack(fill="x", pady=(0, 6))
        self.plan_status_label = ttk.Label(result_frame, text="Noch kein Ablauf berechnet.")
        self.plan_status_label.pack(anchor="w", pady=(0, 8))
        self.plan_cards_frame = ttk.Frame(result_frame)
        self.plan_cards_frame.pack(fill="both", expand=True)
        self.plan_start_button = ttk.Button(
            result_frame,
            text="Ersten Planpunkt starten",
            style="Primary.TButton",
            command=self.start_first_shift_plan_item,
        )
        self.plan_start_button.pack(fill="x", pady=(8, 0))

    def _parsed_plan_start(self) -> datetime:
        return parse_plan_start(self.plan_start.get(), self._plan_date)

    def _update_plan_value_label(self, _event=None) -> None:
        labels = {
            "Bis Schichtende begrenzen": "Maximale Stückzahl (leer = alle offenen):",
            "Feste Stückzahl (Überzeit möglich)": "Feste Stückzahl:",
            "Restschicht mit Auftrag füllen": "Keine Eingabe nötig:",
            "Guthaben nach Stück": "Guthaben-Stückzahl:",
            "Guthaben nach Minuten": "Guthaben-Minuten:",
        }
        self.plan_value_label.configure(text=labels.get(self.plan_mode.get(), "Wert:"))

    def refresh_plan_orders(self) -> None:
        self._plan_order_map = {}
        values = []
        for order in self.database.list_orders():
            label = (
                f"#{order['id']} · {order['order_number']} · {order['die_number']}/{order['operation']} · "
                f"offen {order['open_quantity']} · Guthaben {order['credit_quantity']}"
            )
            values.append(label)
            self._plan_order_map[label] = order
        self.plan_order.configure(values=values)

    def add_shift_plan_item(self) -> None:
        order = getattr(self, "_plan_order_map", {}).get(self.plan_order.get())
        if order is None:
            messagebox.showerror("Keine Auswahl", "Bitte einen Auftrag auswählen.", parent=self)
            return
        modes = {
            "Bis Schichtende begrenzen": "work_capped",
            "Feste Stückzahl (Überzeit möglich)": "work_fixed",
            "Restschicht mit Auftrag füllen": "work_fill",
            "Guthaben nach Stück": "credit_quantity",
            "Guthaben nach Minuten": "credit_time",
        }
        mode = modes[self.plan_mode.get()]
        try:
            if mode == "work_fill":
                value = None
            elif mode == "credit_time":
                value = minutes_to_seconds(self.plan_value.get())
            elif mode == "work_capped" and not self.plan_value.get().strip():
                value = int(order["open_quantity"])
                if value <= 0:
                    raise ValueError
            else:
                value = int(self.plan_value.get())
                if value <= 0:
                    raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("Eingabe prüfen", "Bitte eine gültige Stückzahl oder Minutenzahl eingeben.", parent=self)
            return
        self.shift_plan_items.append({
            "order_id": int(order["id"]), "mode": mode, "value": value,
            "label": self.plan_mode.get(), "order": order,
        })
        self.refresh_shift_plan_queue()
        self.calculate_shift_plan()

    def add_manual_shift_plan_item(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Manuellen Planauftrag eintragen")
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=16); body.pack(fill="both", expand=True)
        fields = (
            ("Auftragsnummer (optional)", ""), ("Gesenknummer", "MANUELL"),
            ("Arbeitsgang", "MANUELL"), ("Stückzahl", ""),
            ("min/Stück", ""), ("Abweichende Startzeit (meist leer)", ""), ("Notiz", ""),
        )
        entries = []
        for row, (label, value) in enumerate(fields):
            ttk.Label(body, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=5)
            entry = ttk.Entry(body, width=38); entry.insert(0, value)
            entry.grid(row=row, column=1, padx=(12, 0), pady=5); entries.append(entry)
        catalog_hint = ttk.Label(body, text="", style="Muted.TLabel")
        catalog_hint.grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Label(
            body,
            text="Leer lassen: Start folgt automatisch auf den vorherigen Auftrag.",
            style="Muted.TLabel",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(2, 4))

        def apply_catalog_time(_event=None) -> None:
            die = entries[1].get().strip()
            operation = entries[2].get().strip()
            matches = self.database.standards_for_die(die) if die else []
            operation_is_placeholder = operation.casefold() == "manuell"
            if operation and not operation_is_placeholder:
                matches = [
                    item for item in matches
                    if item["operation_code"].casefold() == operation.casefold()
                ]
            if len(matches) == 1:
                seconds = int(matches[0]["seconds_per_piece"])
                self._set_entry(entries[4], str(seconds_to_minutes(seconds)).replace(".", ","))
                if not operation or operation_is_placeholder:
                    self._set_entry(entries[2], matches[0]["operation_code"])
                catalog_hint.configure(text="Stückzeit automatisch aus dem Gesenk-Katalog übernommen.")
            elif len(matches) > 1:
                codes = ", ".join(item["operation_code"] for item in matches)
                catalog_hint.configure(text=f"Mehrere Arbeitsgänge vorhanden: {codes}")
            else:
                catalog_hint.configure(text="")

        entries[1].bind("<FocusOut>", apply_catalog_time)
        entries[2].bind("<FocusOut>", apply_catalog_time)
        entries[1].bind("<Return>", apply_catalog_time)
        entries[2].bind("<Return>", apply_catalog_time)
        save_order = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            body, text="Zusätzlich dauerhaft unter Aufträge speichern", variable=save_order
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 4))

        def add() -> None:
            try:
                apply_catalog_time()
                quantity = int(entries[3].get())
                if not entries[4].get().strip():
                    raise ValueError(
                        "Keine eindeutige Stückzeit gefunden. Bitte Arbeitsgang prüfen "
                        "oder min/Stück manuell eingeben."
                    )
                seconds = minutes_to_seconds(entries[4].get())
                if quantity <= 0:
                    raise ValueError("Die Stückzahl muss größer als null sein.")
                plan_start = self._parsed_plan_start()
                start_override = parse_plan_start_override(entries[5].get(), plan_start) if entries[5].get().strip() else None
                number = entries[0].get().strip() or f"PLAN-{datetime.now():%Y%m%d-%H%M%S-%f}"
                if self.database.find_order(number) is not None:
                    raise ValueError("Diese Auftragsnummer ist bereits vorhanden.")
                order_id = self.database.create_order(
                    order_number=number,
                    die_number=entries[1].get().strip() or "MANUELL",
                    operation=entries[2].get().strip() or "MANUELL",
                    original_quantity=quantity,
                    seconds_per_piece=seconds,
                    note=entries[6].get(),
                    is_temporary=not save_order.get(),
                )
                order = self.database.get_order(order_id)
                self.shift_plan_items.append({
                    "order_id": order_id, "mode": "work_capped", "value": quantity,
                    "label": "Bis Schichtende begrenzen", "order": order,
                    "start_override": start_override,
                })
            except (ValueError, TypeError) as error:
                messagebox.showerror("Planauftrag nicht angelegt", str(error), parent=dialog); return
            dialog.destroy(); self.refresh_shift_plan_queue(); self.refresh_plan_orders()
            self.calculate_shift_plan()

        actions = ttk.Frame(body)
        actions.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Abbrechen", command=dialog.destroy).pack(side="left")
        ttk.Button(
            actions, text="ZUM SCHICHTABLAUF HINZUFÜGEN",
            style="Primary.TButton", command=add,
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def edit_plan_item_start(self) -> None:
        selected = self.plan_queue.selection()
        if not selected:
            messagebox.showinfo("Keine Auswahl", "Bitte einen Planpunkt auswählen.", parent=self)
            return
        item = self.shift_plan_items[int(selected[0])]
        current = item.get("start_override")
        value = simpledialog.askstring(
            "Eigene Startzeit",
            "Nur Uhrzeit eingeben, z. B. 13:45. Leer = automatisch anschließend:",
            initialvalue=current.strftime("%H:%M") if isinstance(current, datetime) else "",
            parent=self,
        )
        if value is None:
            return
        try:
            plan_start = self._parsed_plan_start()
            item["start_override"] = parse_plan_start_override(value, plan_start) if value.strip() else None
        except ValueError as error:
            messagebox.showerror("Ungültige Startzeit", str(error), parent=self); return
        self.refresh_shift_plan_queue()
        self._refresh_plan_after_change()

    def _selected_plan_index(self) -> int | None:
        selected = self.plan_queue.selection()
        return int(selected[0]) if selected else None

    def edit_shift_plan_item(self, index: int | None = None) -> None:
        index = self._selected_plan_index() if index is None else index
        if index is None or index < 0 or index >= len(self.shift_plan_items):
            messagebox.showinfo("Keine Auswahl", "Bitte einen Planpunkt auswählen.", parent=self)
            return
        item = self.shift_plan_items[index]
        dialog = tk.Toplevel(self)
        dialog.title("Planpunkt bearbeiten")
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=16); body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text=f"{item['order']['order_number']} · {item['order']['die_number']}/{item['order']['operation']}",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        modes = (
            "Bis Schichtende begrenzen", "Feste Stückzahl (Überzeit möglich)",
            "Restschicht mit Auftrag füllen", "Guthaben nach Stück", "Guthaben nach Minuten",
        )
        ttk.Label(body, text="Planungsart:").grid(row=1, column=0, sticky="w", pady=5)
        mode_entry = ttk.Combobox(body, values=modes, state="readonly", width=34)
        mode_entry.set(item["label"]); mode_entry.grid(row=1, column=1, padx=(12, 0), pady=5)
        ttk.Label(body, text="Stück/Minuten:").grid(row=2, column=0, sticky="w", pady=5)
        value_entry = ttk.Entry(body, width=36)
        if item.get("value") is not None:
            shown = seconds_to_minutes(item["value"]) if item["mode"] == "credit_time" else item["value"]
            value_entry.insert(0, str(shown).replace(".", ","))
        value_entry.grid(row=2, column=1, padx=(12, 0), pady=5)
        ttk.Label(body, text="Abweichende Startzeit:").grid(row=3, column=0, sticky="w", pady=5)
        start_entry = ttk.Entry(body, width=36)
        if isinstance(item.get("start_override"), datetime):
            start_entry.insert(0, item["start_override"].strftime("%H:%M"))
        start_entry.grid(row=3, column=1, padx=(12, 0), pady=5)

        def save() -> None:
            mode_map = {
                "Bis Schichtende begrenzen": "work_capped",
                "Feste Stückzahl (Überzeit möglich)": "work_fixed",
                "Restschicht mit Auftrag füllen": "work_fill",
                "Guthaben nach Stück": "credit_quantity",
                "Guthaben nach Minuten": "credit_time",
            }
            mode = mode_map[mode_entry.get()]
            try:
                if mode == "work_fill":
                    value = None
                elif mode == "credit_time":
                    value = minutes_to_seconds(value_entry.get())
                else:
                    value = int(value_entry.get())
                    if value <= 0:
                        raise ValueError
                start = (
                    parse_plan_start_override(start_entry.get(), self._parsed_plan_start())
                    if start_entry.get().strip() else None
                )
            except (ValueError, TypeError):
                messagebox.showerror(
                    "Eingabe prüfen", "Bitte eine gültige Menge, Minuten- oder Startzeit eingeben.",
                    parent=dialog,
                )
                return
            item.update(mode=mode, value=value, label=mode_entry.get(), start_override=start)
            dialog.destroy()
            self.refresh_shift_plan_queue()
            self._refresh_plan_after_change()

        actions = ttk.Frame(body); actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(actions, text="Abbrechen", command=dialog.destroy).pack(side="left")
        ttk.Button(actions, text="Änderungen übernehmen", style="Primary.TButton", command=save).pack(
            side="right", padx=(10, 0)
        )

    def duplicate_shift_plan_item(self, index: int) -> None:
        if index < 0 or index >= len(self.shift_plan_items):
            return
        original = self.shift_plan_items[index]
        duplicate = {
            key: value for key, value in original.items()
            if key != "plan_item_id"
        }
        duplicate["start_override"] = None
        self.shift_plan_items.insert(index + 1, duplicate)
        self.refresh_shift_plan_queue()
        self._refresh_plan_after_change()

    def _refresh_plan_after_change(self) -> None:
        if not self.shift_plan_items:
            self.shift_plan_results.clear()
            self.database.discard_shift_plan()
            self.render_shift_plan_cards([])
            return
        self.calculate_shift_plan()

    def move_plan_item(self, direction: int) -> None:
        selected = self.plan_queue.selection()
        if not selected:
            return
        self.move_shift_plan_item_at(int(selected[0]), direction)

    def move_shift_plan_item_at(self, source: int, direction: int) -> None:
        target = source + direction
        if target < 0 or target >= len(self.shift_plan_items):
            return
        item = self.shift_plan_items.pop(source)
        self.shift_plan_items.insert(target, item)
        self.refresh_shift_plan_queue()
        self.plan_queue.selection_set(str(target))
        self._refresh_plan_after_change()

    def _plan_drag_start(self, event) -> None:
        row = self.plan_queue.identify_row(event.y)
        self._plan_drag_source = int(row) if row else None

    def _plan_drag_release(self, event) -> None:
        source = self._plan_drag_source
        self._plan_drag_source = None
        target_row = self.plan_queue.identify_row(event.y)
        if source is None or not target_row:
            return
        target = int(target_row)
        if source == target:
            return
        item = self.shift_plan_items.pop(source)
        self.shift_plan_items.insert(target, item)
        self.refresh_shift_plan_queue()
        self.plan_queue.selection_set(str(target))
        self._refresh_plan_after_change()

    def refresh_shift_plan_queue(self) -> None:
        self.plan_queue.delete(*self.plan_queue.get_children())
        for position, item in enumerate(self.shift_plan_items, start=1):
            value = item["value"]
            if item["mode"] == "credit_time" and value is not None:
                value = f"{seconds_to_minutes(value)} min"
            elif value is None:
                value = "automatisch"
            self.plan_queue.insert(
                "", "end", iid=str(position - 1), values=(
                    position, item["order"]["order_number"],
                    f"{item['order']['die_number']}/{item['order']['operation']}",
                    item["label"], value,
                    item.get("start_override").strftime("%d.%m. %H:%M")
                    if isinstance(item.get("start_override"), datetime) else "automatisch",
                )
            )

    def remove_shift_plan_item(self, index: int | None = None) -> None:
        index = self._selected_plan_index() if index is None else index
        if index is None or index < 0 or index >= len(self.shift_plan_items):
            return
        del self.shift_plan_items[index]
        self.refresh_shift_plan_queue()
        self._refresh_plan_after_change()

    def clear_shift_plan(self) -> None:
        self.shift_plan_items.clear()
        self.shift_plan_results.clear()
        self.database.discard_shift_plan()
        self.plan_saved_label.configure(text="")
        self.refresh_shift_plan_queue()
        self.render_shift_plan_cards([])

    def calculate_shift_plan(self, persist: bool = True) -> None:
        self.shift_plan_results = []
        try:
            reported_start = self._parsed_plan_start()
            custom_shift_end = (
                parse_plan_start_override(self.plan_custom_end.get(), reported_start)
                if self.plan_custom_end.get().strip() else None
            )
            self.shift_plan_results = self.service.plan_sequence(
                items=self.shift_plan_items,
                reported_start=reported_start,
                shift_number=int(self.plan_shift.get()),
                custom_shift_end=custom_shift_end,
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Planung nicht möglich", str(error), parent=self)
            return
        if persist:
            try:
                self.database.save_shift_plan(
                    reported_start=reported_start,
                    shift_number=int(self.plan_shift.get()),
                    items=self.shift_plan_items,
                    custom_shift_end=custom_shift_end,
                )
                self.load_persisted_shift_plan(recalculate=False)
                self.plan_saved_label.configure(text="✓ lokal gespeichert")
            except ValueError as error:
                messagebox.showerror("Plan nicht gespeichert", str(error), parent=self)
                return
        self.render_shift_plan_cards(self.shift_plan_results)

    def render_shift_plan_cards(self, results: list[dict]) -> None:
        for child in self.plan_cards_frame.winfo_children():
            child.destroy()
        if not results:
            self.plan_total_label.configure(text="Gesamtzeit: –")
            self.plan_capacity_bar["value"] = 0
            self.plan_status_label.configure(text="Noch kein Ablauf berechnet.")
            ttk.Label(
                self.plan_cards_frame,
                text="Planpunkte hinzufügen und anschließend die Schicht berechnen.",
                style="Muted.TLabel",
            ).pack(anchor="w", pady=10)
            return
        first_start = results[0]["planned_start"]
        last_end = results[-1]["planned_end"]
        productive_seconds = sum(int(item["productive_seconds"]) for item in results)
        custom_shift_end = (
            parse_plan_start_override(self.plan_custom_end.get(), first_start)
            if self.plan_custom_end.get().strip() else None
        )
        shift = with_custom_shift_end(
            self.service.shift_for_start(int(self.plan_shift.get()), first_start), custom_shift_end
        )
        shift_capacity = max(
            int(productive_duration_between(first_start, shift.end, shift.breaks).total_seconds()),
            0,
        )
        free_capacity = max(shift_capacity - productive_seconds, 0)
        utilization = min((productive_seconds / shift_capacity * 100) if shift_capacity else 0, 100)
        self.plan_capacity_bar["value"] = utilization
        overtime_seconds = max(productive_seconds - shift_capacity, 0)
        if overtime_seconds:
            status_text = f"⚠ Plan enthält {format_duration(overtime_seconds)} Überzeit."
        elif free_capacity == 0:
            status_text = "✓ Schicht vollständig verplant."
        elif free_capacity <= 5 * 60:
            status_text = f"✓ Schicht nahezu vollständig geplant · {format_duration(free_capacity)} frei."
        else:
            status_text = (
                f"Noch {format_duration(free_capacity)} produktive Zeit frei – "
                "ein weiterer Auftrag kann eingeplant werden."
            )
        self.plan_status_label.configure(text=status_text)
        self.plan_total_label.configure(
            text=(
                f"Gesamtablauf {first_start:%H:%M}–{last_end:%H:%M} · "
                f"{format_duration(int((last_end - first_start).total_seconds()))} Uhrzeit · "
                f"{format_duration(productive_seconds)} von {format_duration(shift_capacity)} produktiv · "
                f"noch {format_duration(free_capacity)} frei"
            )
        )
        for index, item in enumerate(results):
            row = ttk.Frame(self.plan_cards_frame)
            row.pack(fill="x", pady=4)
            rail = tk.Canvas(row, width=54, height=78, highlightthickness=0, bg="#f0f0f0")
            rail.pack(side="left", fill="y")
            rail.create_oval(9, 8, 45, 44, fill="#2f6fed", outline="")
            rail.create_text(27, 26, text=str(index + 1), fill="white", font=("Segoe UI", 10, "bold"))
            if index < len(results) - 1:
                rail.create_line(27, 44, 27, 78, fill="#2f6fed", width=3)
            card = ttk.LabelFrame(row, padding=10)
            card.pack(side="left", fill="x", expand=True)
            heading = ttk.Frame(card); heading.pack(fill="x")
            ttk.Label(
                heading, text=f"{item['order_number']} · {item['die_number']}/{item['operation']}",
                font=("Segoe UI", 11, "bold"),
            ).pack(side="left")
            ttk.Label(
                heading, text=f"{item['planned_start']:%H:%M}  →  {item['planned_end']:%H:%M}",
                font=("Segoe UI", 11, "bold"),
            ).pack(side="right")
            kind = "Guthaben" if item["kind"] == "credit" else "Bearbeitung"
            overtime = f" · {item['overtime_seconds'] // 60} Min. Überzeit" if item["overtime_seconds"] else ""
            remaining = (
                f" · danach {item['remaining_after_plan']} Stück offen"
                if item["kind"] == "work" else ""
            )
            ttk.Label(
                card,
                text=(
                    f"{kind} · {item['quantity']} ganze Stück · "
                    f"{format_piece_equivalent(item['piece_equivalent'])} rechnerisch · "
                    f"{format_duration(item['productive_seconds'])}{remaining}{overtime}"
                ),
                style="Muted.TLabel",
            ).pack(anchor="w", pady=(5, 0))
            actions = ttk.Frame(card); actions.pack(fill="x", pady=(7, 0))
            ttk.Button(
                actions, text="Bearbeiten", command=lambda i=index: self.edit_shift_plan_item(i)
            ).pack(side="left")
            ttk.Button(
                actions, text="Duplizieren", command=lambda i=index: self.duplicate_shift_plan_item(i)
            ).pack(side="left", padx=4)
            ttk.Button(
                actions, text="▲", width=3,
                command=lambda i=index: self.move_shift_plan_item_at(i, -1),
            ).pack(side="left")
            ttk.Button(
                actions, text="▼", width=3,
                command=lambda i=index: self.move_shift_plan_item_at(i, 1),
            ).pack(side="left", padx=4)
            ttk.Button(
                actions, text="Entfernen", command=lambda i=index: self.remove_shift_plan_item(i)
            ).pack(side="right")

    def start_first_shift_plan_item(self) -> None:
        self.calculate_shift_plan(persist=not bool(
            self.shift_plan_items and self.shift_plan_items[0].get("plan_item_id")
        ))
        if not self.shift_plan_results:
            return
        item = self.shift_plan_results[0]
        if item["quantity"] <= 0:
            messagebox.showerror("Kein Start", "Für diesen Planpunkt ist keine ganze Stückzahl verfügbar.", parent=self)
            return
        try:
            if item["kind"] == "credit":
                if item["mode"] == "credit_time":
                    self.service.start_credit(
                        order_id=item["order_id"], reported_start=item["planned_start"],
                        shift_number=int(self.plan_shift.get()),
                        productive_seconds=item["productive_seconds"],
                    )
                else:
                    self.service.start_credit(
                        order_id=item["order_id"], reported_start=item["planned_start"],
                        shift_number=int(self.plan_shift.get()), quantity=item["quantity"],
                    )
            else:
                session_id = self.service.start_work(
                    order_id=item["order_id"], quantity=item["quantity"],
                    reported_start=item["planned_start"], shift_number=int(self.plan_shift.get()),
                )
            if item["kind"] == "credit":
                session_id = int(self.database.active_session()["id"])
            self.database.link_shift_plan_session(
                int(self.shift_plan_items[0]["plan_item_id"]), int(session_id)
            )
        except ValueError as error:
            messagebox.showerror("Start nicht möglich", str(error), parent=self)
            return
        del self.shift_plan_items[0]
        self._plan_date = item["planned_end"].date()
        self._set_entry(self.plan_start, item["planned_end"].strftime("%H:%M"))
        self.refresh_shift_plan_queue()
        self.notified_session_id = None
        self.refresh_all()
        self.tabs.select(self.dashboard_tab)

    def load_persisted_shift_plan(self, *, recalculate: bool = True) -> None:
        plan = self.database.active_shift_plan()
        if plan is None:
            return
        self._set_entry(
            self.plan_custom_end,
            datetime.fromisoformat(plan["custom_shift_end"]).strftime("%H:%M")
            if plan.get("custom_shift_end") else "",
        )
        labels = {
            "work_capped": "Bis Schichtende begrenzen",
            "work_fixed": "Feste Stückzahl (Überzeit möglich)",
            "work_fill": "Restschicht mit Auftrag füllen",
            "credit_quantity": "Guthaben nach Stück",
            "credit_time": "Guthaben nach Minuten",
        }
        self.shift_plan_items = []
        for saved in plan["items"]:
            if saved["status"] != "offen":
                continue
            order = self.database.get_order(int(saved["order_id"]))
            if order is None:
                continue
            self.shift_plan_items.append({
                "plan_item_id": int(saved["id"]),
                "order_id": int(saved["order_id"]),
                "mode": saved["mode"],
                "value": saved["value"],
                "label": labels[saved["mode"]],
                "order": order,
                "start_override": (
                    datetime.fromisoformat(saved["start_override"])
                    if saved.get("start_override") else None
                ),
            })
        active = self.database.active_session()
        effective_start = (
            datetime.fromisoformat(active["target_end"])
            if active is not None else datetime.fromisoformat(plan["reported_start"])
        )
        self._plan_date = effective_start.date()
        self._set_entry(self.plan_start, effective_start.strftime("%H:%M"))
        self.plan_shift.set(str(plan["shift_number"]))
        self.refresh_shift_plan_queue()
        self.plan_saved_label.configure(text="✓ gespeicherten Plan geladen")
        self.plan_start_button.configure(state="disabled" if active is not None else "normal")
        if recalculate and self.shift_plan_items:
            self.calculate_shift_plan(persist=False)

    def _refresh_quick_dies(self) -> None:
        dies = sorted({item["die_number"] for item in self.database.list_catalog()})
        self.quick_entries[2].configure(values=dies)

    def _quick_die_selected(self, _event=None) -> None:
        standards = self.database.standards_for_die(self.quick_entries[2].get())
        self.quick_entries[3].configure(values=tuple(item["operation_code"] for item in standards))
        if len(standards) == 1:
            self.quick_entries[3].set(standards[0]["operation_code"])
        else:
            self.quick_entries[3].set("")

    def quick_start(self) -> None:
        try:
            minutes = self.quick_entries[1].get().strip()
            result = self.service.quick_start(
                total_quantity=int(self.quick_entries[0].get()),
                seconds_per_piece=minutes_to_seconds(minutes) if minutes else None,
                die_number=self.quick_entries[2].get(),
                operation=self.quick_entries[3].get(),
                order_number=self.quick_entries[4].get(),
                reported_start=parse_datetime(self.quick_entries[5].get()),
                shift_number=int(self.quick_entries[6].get()),
                note=self.quick_note.get(),
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Schnellstart nicht möglich", str(error), parent=self)
            return
        self.notified_session_id = None
        self.refresh_all()
        self.tabs.select(self.dashboard_tab)
        messagebox.showinfo(
            "Arbeitseinsatz gestartet",
            f"{result['order_number']} · {result['planned_quantity']} Stück für diesen Einsatz · "
            f"Vorgabe aus {result['source']}",
            parent=self,
        )

    def _build_catalog(self) -> None:
        form = ttk.LabelFrame(self.catalog_tab, text="Vorgabe anlegen oder aktualisieren", padding=12)
        form.pack(fill="x")
        fields = (
            "Gesenknummer", "AG-Code", "Bezeichnung (optional)",
            "min/Stück", "Gesenkbeschreibung (optional)",
        )
        self.catalog_entries: list[ttk.Entry] = []
        for column, label in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=4)
            entry = ttk.Entry(form, width=18)
            entry.grid(row=1, column=column, sticky="ew", padx=4, pady=(3, 8))
            self.catalog_entries.append(entry)
            form.columnconfigure(column, weight=1)
        ttk.Label(form, text="Notiz zum Gesenk").grid(row=2, column=0, sticky="w", padx=4)
        self.catalog_note = ttk.Entry(form)
        self.catalog_note.grid(row=3, column=0, columnspan=4, sticky="ew", padx=4)
        ttk.Button(form, text="Vorgabe speichern", command=self.save_catalog_standard).grid(
            row=3, column=4, sticky="ew", padx=4
        )

        tools = ttk.Frame(self.catalog_tab)
        tools.pack(fill="x", pady=(14, 8))
        ttk.Label(tools, text="Katalog durchsuchen:").pack(side="left")
        self.catalog_search = ttk.Entry(tools, width=30)
        self.catalog_search.pack(side="left", padx=8)
        self.catalog_search.bind("<Return>", lambda _event: self.refresh_catalog())
        ttk.Button(tools, text="Suchen", command=self.refresh_catalog).pack(side="left")
        ttk.Button(tools, text="Alle anzeigen", command=self.reset_catalog_search).pack(
            side="left", padx=8
        )
        ttk.Button(tools, text="Ausgewählte Vorgabe deaktivieren", command=self.deactivate_catalog_standard).pack(
            side="right"
        )

        columns = ("id", "die", "description", "code", "name", "time")
        self.catalog_tree = ttk.Treeview(
            self.catalog_tab, columns=columns, show="headings", height=16
        )
        headings = ("ID", "Gesenk", "Beschreibung", "AG", "Arbeitsgang", "Vorgabe")
        widths = (45, 100, 190, 70, 210, 100)
        for column, heading, width in zip(columns, headings, widths):
            self.catalog_tree.heading(column, text=heading)
            self.catalog_tree.column(column, width=width, anchor="center")
        self.catalog_tree.pack(fill="both", expand=True)
        self.catalog_tree.bind("<Double-1>", self.load_catalog_selection)

    def _build_history(self) -> None:
        filters = ttk.Frame(self.history_tab)
        filters.pack(fill="x", pady=(0, 10))
        ttk.Label(filters, text="Suche:").pack(side="left")
        self.history_search = ttk.Entry(filters, width=28)
        self.history_search.pack(side="left", padx=(6, 16))
        self.history_search.bind("<Return>", lambda _event: self.refresh_history())
        ttk.Label(filters, text="Status:").pack(side="left")
        self.history_status = ttk.Combobox(
            filters,
            values=("Alle", "laufend", "abgeschlossen", "abgebrochen", "korrigiert"),
            state="readonly",
            width=16,
        )
        self.history_status.set("Alle")
        self.history_status.pack(side="left", padx=6)
        ttk.Button(filters, text="Filtern", command=self.refresh_history).pack(side="left", padx=6)
        ttk.Button(filters, text="Zurücksetzen", command=self.reset_history_filter).pack(side="left")
        columns = (
            "date", "order", "die", "operation", "times", "quantity",
            "time_result", "quantity_result", "status",
        )
        self.history_tree = ttk.Treeview(
            self.history_tab, columns=columns, show="headings", height=18
        )
        headings = (
            "Datum", "Auftrag", "Gesenk", "AG", "An-/Abmeldung", "Bearb./Rückm./Plan",
            "Zeitabweichung", "Stückabweichung", "Status",
        )
        widths = (80, 105, 70, 50, 145, 115, 205, 175, 100)
        for column, heading, width in zip(columns, headings, widths):
            self.history_tree.heading(column, text=heading)
            self.history_tree.column(column, width=width, anchor="center")
        self.history_tree.pack(fill="both", expand=True)
        actions = ttk.Frame(self.history_tab)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Details", command=self.show_history_details).pack(side="left")
        ttk.Button(actions, text="Rückmeldung korrigieren", command=self.edit_history_entry).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Auftragsdaten ergänzen", command=self.edit_history_order).pack(
            side="left"
        )
        ttk.Button(actions, text="Korrekturprotokoll", command=self.show_session_corrections).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Stornieren", command=self.void_history_entry).pack(
            side="left"
        )
        ttk.Button(actions, text="Storno-Papierkorb", command=self.open_history_trash).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Historie aktualisieren", command=self.refresh_history).pack(
            side="right"
        )
        self.history_tree.bind("<Double-1>", self.show_history_details)

    @staticmethod
    def _entry_datetime(entry: ttk.Entry) -> datetime:
        return parse_datetime(entry.get())

    @staticmethod
    def _set_entry(entry: ttk.Entry, value: str) -> None:
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def _fill_start_now(self) -> None:
        self._set_entry(self.start_time, local_now().strftime("%Y-%m-%d %H:%M"))
        if hasattr(self, "start_forecast"):
            self.refresh_start_forecast(apply_recommendation=True)

    def _fill_finish_now(self) -> None:
        self._set_entry(self.finish_time, local_now().strftime("%Y-%m-%d %H:%M"))

    def create_order(self) -> None:
        try:
            number, die, operation, quantity, minutes = (e.get().strip() for e in self.order_entries)
            self.service.create_order(
                order_number=number,
                die_number=die,
                operation=operation,
                original_quantity=int(quantity),
                seconds_per_piece=minutes_to_seconds(minutes),
                note=self.order_note.get(),
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Eingabe prüfen", str(error), parent=self)
            return
        for entry in self.order_entries:
            entry.delete(0, tk.END)
        self.order_note.delete(0, tk.END)
        self.refresh_order_total_time()
        self.refresh_orders()
        messagebox.showinfo("Gespeichert", "Der Auftrag wurde lokal angelegt.", parent=self)

    def _refresh_die_suggestions(self) -> None:
        dies = sorted({item["die_number"] for item in self.database.list_catalog()})
        self.order_entries[1].configure(values=dies)

    def _catalog_die_selected(self, _event=None) -> None:
        standards = self.database.standards_for_die(self.order_entries[1].get())
        self._current_die_standards = {item["operation_code"]: item for item in standards}
        self.order_entries[2].configure(values=tuple(self._current_die_standards))
        self.order_entries[2].set("")

    def _catalog_operation_selected(self, _event=None) -> None:
        standard = getattr(self, "_current_die_standards", {}).get(self.order_entries[2].get())
        if standard is None:
            return
        self._set_entry(
            self.order_entries[4], str(seconds_to_minutes(standard["seconds_per_piece"]))
        )
        self.refresh_order_total_time()

    def refresh_order_total_time(self) -> None:
        try:
            quantity = int(self.order_entries[3].get())
            seconds = quantity * minutes_to_seconds(self.order_entries[4].get())
        except (ValueError, TypeError):
            self.order_total_time.configure(text="Gesamtvorgabezeit: –")
            return
        self.order_total_time.configure(
            text=f"Gesamtvorgabezeit des Auftrags: {format_total_target_time(seconds)}"
        )

    def save_catalog_standard(self) -> None:
        try:
            die, code, name, minutes, description = (entry.get() for entry in self.catalog_entries)
            self.database.save_standard(
                die_number=die,
                operation_code=code,
                operation_name=name,
                seconds_per_piece=minutes_to_seconds(minutes),
                die_description=description,
                die_note=self.catalog_note.get(),
            )
        except ValueError as error:
            messagebox.showerror("Vorgabe nicht gespeichert", str(error), parent=self)
            return
        for entry in self.catalog_entries:
            entry.delete(0, tk.END)
        self.catalog_note.delete(0, tk.END)
        self.refresh_catalog()
        self._refresh_die_suggestions()

    def refresh_catalog(self) -> None:
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        search = self.catalog_search.get() if hasattr(self, "catalog_search") else ""
        for item in self.database.list_catalog(search=search):
            self.catalog_tree.insert(
                "", "end", iid=str(item["id"]), values=(
                    item["id"], item["die_number"], item["description"],
                    item["operation_code"], item["operation_name"],
                    f"{seconds_to_minutes(item['seconds_per_piece'])} min",
                )
            )

    def reset_catalog_search(self) -> None:
        self.catalog_search.delete(0, tk.END)
        self.refresh_catalog()

    def load_catalog_selection(self, _event=None) -> None:
        selected = self.catalog_tree.selection()
        if not selected:
            return
        standard_id = int(selected[0])
        item = next(
            (entry for entry in self.database.list_catalog() if entry["id"] == standard_id), None
        )
        if item is None:
            return
        values = (
            item["die_number"], item["operation_code"], item["operation_name"],
            str(seconds_to_minutes(item["seconds_per_piece"])), item["description"],
        )
        for entry, value in zip(self.catalog_entries, values):
            self._set_entry(entry, value)
        self._set_entry(self.catalog_note, item["die_note"])

    def deactivate_catalog_standard(self) -> None:
        selected = self.catalog_tree.selection()
        if not selected:
            messagebox.showerror("Keine Auswahl", "Bitte eine Vorgabe auswählen.", parent=self)
            return
        if not messagebox.askyesno(
            "Vorgabe deaktivieren",
            "Die Vorgabe wird bei neuen Aufträgen nicht mehr vorgeschlagen. Historische Daten bleiben erhalten.",
            parent=self,
        ):
            return
        self.database.deactivate_standard(int(selected[0]))
        self.refresh_catalog()

    def selected_order_id(self) -> int:
        selected = self.orders_tree.selection()
        if not selected:
            raise ValueError("Bitte zuerst einen Auftrag in der Liste auswählen.")
        return int(self.orders_tree.item(selected[0], "values")[0])

    def _order_selected(self, _event=None) -> None:
        try:
            order = self.database.get_order(self.selected_order_id())
        except ValueError:
            return
        if order is None:
            return
        self.refresh_start_forecast(apply_recommendation=True)

    def refresh_start_forecast(self, *, apply_recommendation: bool = False) -> None:
        try:
            forecast = self.service.production_forecast(
                order_id=self.selected_order_id(),
                reported_start=self._entry_datetime(self.start_time),
                shift_number=int(self.shift_number.get()),
            )
        except (ValueError, TypeError):
            if hasattr(self, "start_forecast"):
                self.start_forecast.configure(
                    text="Auftrag, Anmeldezeit und Schicht auswählen, um die Sollstückzahl zu berechnen."
                )
            return
        available = format_duration(forecast["available_seconds"])
        equivalent = format_piece_equivalent(forecast["target_equivalent"])
        if apply_recommendation:
            self._set_entry(self.start_quantity, str(forecast["complete_pieces"]))
        text = (
            f"Bis {forecast['shift_end']:%H:%M}: {available} produktiv · "
            f"Sollleistung {equivalent} Stück · "
            f"empfohlener Einsatz {forecast['complete_pieces']} vollständige Stück · "
            f"danach {forecast['open_after_shift']} Stück offen"
        )
        if forecast["open_after_shift"]:
            next_finish = forecast["next_piece_finish"]
            text += (
                f"\nDanach bleiben {format_duration(forecast['remainder_seconds'])} bis Schichtende. "
                f"Ein weiteres Stück wäre um {next_finish:%H:%M} fertig "
                f"({forecast['next_piece_overtime_seconds'] // 60} Min. nach Schichtende)."
            )
        self.start_forecast.configure(text=text)

    def start_selected(self) -> None:
        try:
            order_id = self.selected_order_id()
            shift = int(self.shift_number.get()) if self.shift_number.get() else None
            quantity = int(self.start_quantity.get())
            if shift is not None:
                forecast = self.service.production_forecast(
                    order_id=order_id,
                    reported_start=self._entry_datetime(self.start_time),
                    shift_number=shift,
                )
                if quantity > forecast["complete_pieces"] and not messagebox.askyesno(
                    "Einsatzmenge überschreitet die Restschicht",
                    f"Innerhalb der Schicht sind {forecast['complete_pieces']} Stück vollständig möglich.\n"
                    f"Du hast {quantity} Stück für diesen Einsatz eingetragen.\n\n"
                    "Trotzdem mit dieser Einsatzmenge starten?",
                    parent=self,
                ):
                    return
            self.service.start_work(
                order_id=order_id,
                quantity=quantity,
                reported_start=self._entry_datetime(self.start_time),
                shift_number=shift,
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Start nicht möglich", str(error), parent=self)
            return
        self.notified_session_id = None
        self.tabs.select(self.dashboard_tab)
        self.refresh_all()

    def duplicate_selected_order(self) -> None:
        try:
            new_id = self.database.duplicate_order(self.selected_order_id())
        except ValueError as error:
            messagebox.showerror("Duplizieren nicht möglich", str(error), parent=self)
            return
        self.refresh_orders()
        self.open_order_editor(new_id)

    def archive_selected_order(self) -> None:
        try:
            order_id = self.selected_order_id()
            order = self.database.get_order(order_id)
            if order is None:
                raise ValueError("Auftrag nicht gefunden.")
            if not messagebox.askyesno(
                "Auftrag in Papierkorb verschieben",
                f"{order['order_number']} aus den normalen Listen ausblenden?\n\n"
                "Rückmeldungen und Guthaben bleiben erhalten, bis der Auftrag im Papierkorb "
                "endgültig gelöscht wird.",
                parent=self,
            ):
                return
            self.database.archive_order(order_id)
        except ValueError as error:
            messagebox.showerror("Archivieren nicht möglich", str(error), parent=self)
            return
        self.refresh_all()

    def open_order_trash(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Auftrags-Papierkorb")
        dialog.geometry("780x420")
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Archivierte Aufträge", style="Title.TLabel").pack(anchor="w")
        tree = ttk.Treeview(
            body, columns=("id", "order", "die", "operation", "actual", "reported"),
            show="headings", height=12,
        )
        for column, heading, width in zip(
            ("id", "order", "die", "operation", "actual", "reported"),
            ("ID", "Auftrag", "Gesenk", "AG", "Bearbeitet", "Rückgemeldet"),
            (45, 190, 100, 80, 110, 120),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="center")
        tree.pack(fill="both", expand=True, pady=10)

        def refresh() -> None:
            tree.delete(*tree.get_children())
            for order in self.database.list_orders(include_archived=True):
                if order["status"] == "archiviert":
                    tree.insert("", "end", iid=str(order["id"]), values=(
                        order["id"], order["order_number"], order["die_number"],
                        order["operation"], order["completed_quantity"], order["reported_quantity"],
                    ))

        def selected_id() -> int:
            if not tree.selection():
                raise ValueError("Bitte einen archivierten Auftrag auswählen.")
            return int(tree.selection()[0])

        def restore() -> None:
            try:
                self.database.restore_archived_order(selected_id())
            except ValueError as error:
                messagebox.showerror("Wiederherstellen nicht möglich", str(error), parent=dialog)
                return
            refresh(); self.refresh_all()

        def delete() -> None:
            try:
                order_id = selected_id()
                order = self.database.get_order(order_id)
                if not messagebox.askyesno(
                    "Endgültig löschen",
                    f"{order['order_number']} einschließlich aller zugehörigen Rückmeldungen "
                    "unwiderruflich löschen?",
                    icon="warning", parent=dialog,
                ):
                    return
                self.database.permanently_delete_archived_order(order_id)
            except ValueError as error:
                messagebox.showerror("Löschen nicht möglich", str(error), parent=dialog)
                return
            refresh(); self.refresh_all()

        actions = ttk.Frame(body); actions.pack(fill="x")
        ttk.Button(actions, text="Wiederherstellen", command=restore).pack(side="left")
        ttk.Button(actions, text="Endgültig löschen", command=delete).pack(side="right")
        refresh()

    def edit_selected_order(self) -> None:
        try:
            order_id = self.selected_order_id()
        except ValueError as error:
            messagebox.showerror("Keine Auswahl", str(error), parent=self)
            return
        self.open_order_editor(order_id)

    def open_order_editor(self, order_id: int) -> None:
        try:
            order = self.database.get_order(order_id)
            if order is None:
                raise ValueError("Auftrag nicht gefunden.")
        except ValueError as error:
            messagebox.showerror("Keine Auswahl", str(error), parent=self)
            return

        dialog = tk.Toplevel(self)
        dialog.title(f"Auftrag {order['order_number']} bearbeiten")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        values = (
            ("Auftragsnummer", order["order_number"], True),
            ("Gesenknummer", order["die_number"], True),
            ("Arbeitsgang", order["operation"], True),
            ("Gesamtmenge", str(order["original_quantity"]), True),
            ("Vorgabe min/Stück", str(seconds_to_minutes(order["seconds_per_piece"])), True),
            ("Auftragsnotiz", order["note"], True),
        )
        entries: list[ttk.Entry] = []
        for row, (label, value, enabled) in enumerate(values):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", pady=5)
            entry = ttk.Entry(body, width=38)
            entry.insert(0, value)
            entry.configure(state="normal" if enabled else "disabled")
            entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=5)
            entries.append(entry)
        ttk.Label(
            body,
            text="Bestehende Meldungen behalten immer ihre damalige Vorgabezeit.",
            style="Muted.TLabel",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 4))

        def save() -> None:
            try:
                self.database.update_order(
                    int(order["id"]),
                    order_number=entries[0].get(),
                    die_number=entries[1].get(),
                    operation=entries[2].get(),
                    original_quantity=int(entries[3].get()),
                    seconds_per_piece=minutes_to_seconds(entries[4].get()),
                    note=entries[5].get(),
                )
            except (ValueError, TypeError) as error:
                messagebox.showerror("Änderung nicht möglich", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh_orders()

        buttons = ttk.Frame(body)
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Abbrechen", command=dialog.destroy).pack(side="left", padx=6)
        ttk.Button(buttons, text="Änderungen speichern", style="Primary.TButton", command=save).pack(
            side="left"
        )

    def show_order_corrections(self) -> None:
        try:
            order_id = self.selected_order_id()
        except ValueError as error:
            messagebox.showerror("Keine Auswahl", str(error), parent=self)
            return
        labels = {
            "die_number": "Gesenknummer", "operation": "Arbeitsgang",
            "original_quantity": "Gesamtmenge", "seconds_per_piece": "Vorgabezeit",
            "note": "Notiz", "status": "Status",
        }
        corrections = self.database.corrections("order", order_id)
        if not corrections:
            messagebox.showinfo("Änderungen", "Für diesen Auftrag gibt es keine Änderungen.", parent=self)
            return
        lines = []
        for item in corrections:
            changed = display_time(item["changed_at"])
            field = labels.get(item["field_name"], item["field_name"])
            lines.append(
                f"{changed} · {field}\n  {item['old_value']} → {item['new_value']}\n"
                f"  {item['reason'] or 'ohne Begründung'}"
            )
        messagebox.showinfo("Änderungsprotokoll", "\n\n".join(lines), parent=self)

    def resume_selected(self) -> None:
        try:
            order_id = self.selected_order_id()
            order = self.database.get_order(order_id)
            if order is None or order["status"] != "abgegeben":
                raise ValueError("Bitte einen zuvor abgegebenen Auftrag auswählen.")
            self.database.resume_order(order_id)
        except ValueError as error:
            messagebox.showerror("Wiederaufnahme nicht möglich", str(error), parent=self)
            return
        self.refresh_orders()

    def open_credit_dialog(self) -> None:
        try:
            order = self.database.get_order(self.selected_order_id())
            if order is None:
                raise ValueError("Auftrag nicht gefunden.")
            if int(order["credit_quantity"]) <= 0:
                raise ValueError("Für diesen Auftrag ist kein Guthaben vorhanden.")
        except ValueError as error:
            messagebox.showerror("Kein Guthaben", str(error), parent=self)
            return

        dialog = tk.Toplevel(self)
        dialog.title(f"Guthaben anmelden · {order['order_number']}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        credit_minutes = seconds_to_minutes(
            int(order["credit_quantity"]) * int(order["seconds_per_piece"])
        )
        ttk.Label(
            body,
            text=f"Verfügbar: {order['credit_quantity']} Stück · {credit_minutes} Minuten Guthaben",
            style="Title.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))

        mode = tk.StringVar(value="quantity")
        ttk.Radiobutton(body, text="Nach Stückzahl", variable=mode, value="quantity").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Radiobutton(body, text="Nach exakter Zeit in Minuten", variable=mode, value="time").grid(
            row=1, column=1, columnspan=2, sticky="w"
        )
        ttk.Label(body, text="Stück oder Minuten:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        value_entry = ttk.Entry(body, width=15)
        value_entry.grid(row=2, column=1, sticky="w", pady=(12, 0))
        ttk.Label(body, text="Anmeldezeit:").grid(row=3, column=0, sticky="w", pady=(12, 0))
        start_entry = ttk.Entry(body, width=20)
        start_entry.insert(0, local_now().strftime("%Y-%m-%d %H:%M"))
        start_entry.grid(row=3, column=1, sticky="w", pady=(12, 0))
        ttk.Label(body, text="Schicht:").grid(row=4, column=0, sticky="w", pady=(12, 0))
        shift_entry = ttk.Combobox(body, values=("1", "2", "3"), state="readonly", width=8)
        shift_entry.set(str(self._current_shift_number(local_now())))
        shift_entry.grid(row=4, column=1, sticky="w", pady=(12, 0))
        preview = ttk.Label(
            body,
            text="Bei Zeitvorgabe zeigt WerkMate nach dem Start den Dezimalwert und Rundungsvorschlag.",
            style="Muted.TLabel",
        )
        preview.grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 6))

        def start_credit() -> None:
            try:
                value = value_entry.get().strip()
                result = self.service.start_credit(
                    order_id=int(order["id"]),
                    reported_start=parse_datetime(start_entry.get()),
                    shift_number=int(shift_entry.get()),
                    quantity=int(value) if mode.get() == "quantity" else None,
                    productive_seconds=(
                        minutes_to_seconds(value) if mode.get() == "time" else None
                    ),
                    note="Guthaben angemeldet",
                )
            except (ValueError, TypeError) as error:
                messagebox.showerror("Guthabenstart nicht möglich", str(error), parent=dialog)
                return
            dialog.destroy()
            self.notified_session_id = None
            self.refresh_all()
            self.tabs.select(self.dashboard_tab)
            messagebox.showinfo(
                "Guthaben gestartet",
                f"Geplante Abmeldung: {result['target_end']:%d.%m.%Y %H:%M}\n"
                f"Rechnerisch: {format_piece_equivalent(result['piece_equivalent'])} Stück\n"
                f"Rundungsvorschlag: {result['suggested_quantity']} Stück",
                parent=self,
            )

        buttons = ttk.Frame(body)
        buttons.grid(row=6, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Abbrechen", command=dialog.destroy).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Guthaben jetzt anmelden", style="Primary.TButton", command=start_credit
        ).pack(side="left")

    def hand_off_selected(self) -> None:
        try:
            order_id = self.selected_order_id()
            order = self.database.get_order(order_id)
            if order is None:
                raise ValueError("Auftrag nicht gefunden.")
            active = self.database.active_session()
            if active is not None and int(active["order_id"]) == order_id:
                raise ValueError("Ein laufender Arbeitseinsatz kann nicht abgegeben werden.")
            if not messagebox.askyesno(
                "Restauftrag abgeben",
                f"Den offenen Rest von {order['open_quantity']} Stück nicht mehr persönlich verfolgen?\n\n"
                "Das bedeutet nicht, dass der betriebliche Auftrag erledigt ist.",
                parent=self,
            ):
                return
            self.database.hand_off_order(order_id, reason="Über die Oberfläche abgegeben")
        except ValueError as error:
            messagebox.showerror("Übergabe nicht möglich", str(error), parent=self)
            return
        self.refresh_orders()

    def backup_database(self) -> None:
        proposed = f"WerkMate-Sicherung-{datetime.now():%Y-%m-%d-%H%M}.sqlite3"
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="WerkMate-Daten sichern",
            defaultextension=".sqlite3",
            initialfile=proposed,
            filetypes=(("WerkMate-Datenbank", "*.sqlite3"), ("Alle Dateien", "*.*")),
        )
        if not destination:
            return
        try:
            self.database.backup_to(destination)
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("Sicherung fehlgeschlagen", str(error), parent=self)
            return
        messagebox.showinfo("Sicherung erstellt", f"Gespeichert unter:\n{destination}", parent=self)

    def finish_active(self) -> None:
        session = self.database.active_session()
        if session is None:
            messagebox.showinfo("Kein Auftrag", "Es läuft derzeit kein Arbeitseinsatz.", parent=self)
            return
        try:
            reported_end = self._entry_datetime(self.finish_time)
            warning = warn_unusual_end(session, reported_end)
            if warning and not messagebox.askyesno(
                "Ungewöhnliche Abmeldezeit",
                f"{warning}\n\nZeit trotzdem bewusst übernehmen?",
                parent=self,
            ):
                return
            if session.get("session_kind") == "credit":
                reported_quantity = int(self.finish_reported_quantity.get())
                self.service.finish_credit(
                    int(session["id"]),
                    reported_quantity=reported_quantity,
                    reported_end=reported_end,
                    note=self.finish_note.get(),
                )
            else:
                completed_quantity = int(self.finish_quantity.get())
                reported_text = self.finish_reported_quantity.get().strip()
                self.service.finish_work(
                    int(session["id"]),
                    completed_quantity=completed_quantity,
                    reported_quantity=(int(reported_text) if reported_text else completed_quantity),
                    reported_end=reported_end,
                    note=self.finish_note.get(),
                )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Rückmeldung nicht möglich", str(error), parent=self)
            return
        self.finish_quantity.delete(0, tk.END)
        self.finish_reported_quantity.delete(0, tk.END)
        self.finish_note.delete(0, tk.END)
        self.load_persisted_shift_plan()
        self.refresh_all()
        self._show_finished_and_offer_next(
            "Rückmeldung gespeichert",
            "Bearbeitete und betrieblich rückgemeldete Stück wurden getrennt gespeichert.",
        )

    def finish_entire_order(self) -> None:
        session = self.database.active_session()
        if session is None:
            messagebox.showinfo("Kein Auftrag", "Es läuft derzeit kein Arbeitseinsatz.", parent=self)
            return
        order = self.database.get_order(int(session["order_id"]))
        if order is None:
            messagebox.showerror("Fehler", "Auftrag nicht gefunden.", parent=self)
            return
        open_quantity = int(order["open_quantity"])
        try:
            reported_text = self.finish_reported_quantity.get().strip()
            reported_quantity = int(reported_text) if reported_text else open_quantity
        except ValueError:
            messagebox.showerror(
                "Eingabe prüfen",
                "Die betriebliche Rückmeldemenge muss eine ganze Zahl sein.",
                parent=self,
            )
            return
        if not messagebox.askyesno(
            "Gesamtauftrag vollständig beenden",
            f"Wirklich alle noch offenen {open_quantity} Stück als fertig bearbeitet speichern?\n"
            f"Davon werden heute {reported_quantity} Stück betrieblich rückgemeldet.\n\n"
            f"Neues Guthaben aus diesem Einsatz: {open_quantity - reported_quantity} Stück.",
            parent=self,
        ):
            return
        try:
            reported_end = self._entry_datetime(self.finish_time)
            warning = warn_unusual_end(session, reported_end)
            if warning and not messagebox.askyesno(
                "Ungewöhnliche Abmeldezeit",
                f"{warning}\n\nZeit trotzdem bewusst übernehmen?",
                parent=self,
            ):
                return
            completed = self.service.finish_entire_order(
                int(session["id"]),
                reported_end=reported_end,
                note=self.finish_note.get(),
                reported_quantity=reported_quantity,
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Beenden nicht möglich", str(error), parent=self)
            return
        self.finish_quantity.delete(0, tk.END)
        self.finish_reported_quantity.delete(0, tk.END)
        self.finish_note.delete(0, tk.END)
        self.load_persisted_shift_plan()
        self.refresh_all()
        self._show_finished_and_offer_next(
            "Auftrag vollständig beendet",
            f"Alle {completed} noch offenen Stück wurden als bearbeitet gespeichert. "
            f"Heute rückgemeldet: {reported_quantity} Stück.",
        )

    def _show_finished_and_offer_next(self, title: str, message: str) -> None:
        if self.shift_plan_items:
            next_item = self.shift_plan_results[0] if self.shift_plan_results else None
            next_text = (
                f"\n\nNächster Planpunkt: {next_item['order_number']} ab "
                f"{next_item['planned_start']:%H:%M}.\nDiesen Auftrag jetzt verbindlich anmelden und starten?"
                if next_item else "\n\nIm Schichtplan ist noch ein weiterer Auftrag vorgemerkt."
            )
            if messagebox.askyesno(title, message + next_text, parent=self):
                self.tabs.select(self.plan_tab)
                self.start_first_shift_plan_item()
            return
        messagebox.showinfo(title, message, parent=self)

    def cancel_active(self) -> None:
        session = self.database.active_session()
        if session is None:
            return
        if not messagebox.askyesno(
            "Arbeitseinsatz abbrechen",
            "Diesen Start rückgängig machen? Es werden keine Stück rückgemeldet.\n\n"
            "Der Auftrag bleibt offen und kann anschließend mit korrigierten Eingaben neu gestartet werden.",
            parent=self,
        ):
            return
        try:
            self.service.cancel_work(int(session["id"]), reason="Fehlstart über Oberfläche abgebrochen")
        except ValueError as error:
            messagebox.showerror("Abbruch nicht möglich", str(error), parent=self)
            return
        self.load_persisted_shift_plan()
        self.refresh_all()
        self.tabs.select(self.plan_tab if self.shift_plan_items else self.orders_tab)

    def extend_active_session(self) -> None:
        session = self.database.active_session()
        if session is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title("Neue Endzeit setzen")
        dialog.transient(self); dialog.grab_set(); dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=16); body.pack(fill="both", expand=True)
        previous = datetime.fromisoformat(session["target_end"])
        proposed = max(local_now() + timedelta(minutes=15), previous + timedelta(minutes=15))
        ttk.Label(body, text=f"Bisherige Endzeit: {previous:%d.%m.%Y %H:%M}").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(body, text="Neue Endzeit:").grid(row=1, column=0, sticky="w", pady=5)
        end_entry = ttk.Entry(body, width=24); end_entry.insert(0, proposed.strftime("%Y-%m-%d %H:%M"))
        end_entry.grid(row=1, column=1, padx=(12, 0), pady=5)
        ttk.Label(body, text="Grund (optional):").grid(row=2, column=0, sticky="w", pady=5)
        reason_entry = ttk.Entry(body, width=32); reason_entry.grid(row=2, column=1, padx=(12, 0), pady=5)
        ttk.Label(
            body,
            text="Zur neuen Endzeit ertönt der Alarm erneut. Weitere Verlängerungen bleiben möglich.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 4))

        def save() -> None:
            try:
                self.database.extend_session(
                    int(session["id"]), new_target_end=parse_datetime(end_entry.get()),
                    reason=reason_entry.get(),
                )
            except ValueError as error:
                messagebox.showerror("Endzeit nicht geändert", str(error), parent=dialog); return
            self.notified_session_id = None
            dialog.destroy()
            self.load_persisted_shift_plan()
            self.refresh_all()

        ttk.Button(body, text="NEUE ENDZEIT ÜBERNEHMEN", style="Primary.TButton", command=save).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

    def refresh_orders(self) -> None:
        self.orders_tree.delete(*self.orders_tree.get_children())
        for order in self.database.list_orders():
            self.orders_tree.insert(
                "", "end", values=(
                    order["id"], order["order_number"], order["die_number"],
                    order["operation"],
                    f"{order['completed_quantity']}/{order['original_quantity']}",
                    f"{order['reported_quantity']}/{order['original_quantity']}",
                    f"{order['credit_quantity']} Stk · "
                    f"{seconds_to_minutes(order['credit_quantity'] * order['seconds_per_piece'])} min",
                    f"{order['open_quantity']} Stk",
                    format_total_target_time(
                        int(order["original_quantity"]) * int(order["seconds_per_piece"])
                    ),
                    order["status"],
                )
            )

    def refresh_dashboard(self) -> None:
        status = self.service.status()
        active = status is not None
        for child in self.dashboard_tab.winfo_children()[-1:]:
            for widget in child.winfo_children():
                try:
                    widget.configure(state="normal" if active else "disabled")
                except tk.TclError:
                    pass
        if not active:
            self.active_title.configure(text="Kein laufender Auftrag")
            self.active_details.configure(text="Im Reiter „Aufträge“ kann ein Auftrag gestartet werden.")
            self.countdown_caption.configure(text="")
            self.countdown.configure(text="--:--:--", style="Countdown.TLabel")
            self.target_label.configure(text="")
            self.work_progress.configure(value=0)
            self.extend_work_button.configure(state="disabled")
            self.forecast_label.configure(text="")
            self.order_remaining_label.configure(text="")
            self.cancel_work_button.configure(state="disabled")
            return
        self.cancel_work_button.configure(state="normal")
        self.extend_work_button.configure(state="normal")

        is_credit = status.get("session_kind") == "credit"
        self.finish_actual_label.configure(
            text="Keine neue Bearbeitung:" if is_credit else "Tatsächlich bearbeitet:"
        )
        self.finish_quantity.configure(state="disabled" if is_credit else "normal")
        self.finish_reported_label.configure(
            text="Guthaben jetzt rückmelden:" if is_credit else "Betrieblich rückgemeldet:"
        )
        self.partial_finish_button.configure(
            text="Guthaben rückmelden" if is_credit else "Teilrückmelden / Arbeitseinsatz unterbrechen"
        )
        self.finish_entire_button.configure(state="disabled" if is_credit else "normal")

        self.active_title.configure(
            text=f"{status['order_number']} · Ges. {status['die_number']} · {status['operation']}"
        )
        if is_credit:
            self.active_details.configure(
                text=f"Guthaben-Einsatz #{status['id']} · "
                     f"{format_piece_equivalent(status['credit_piece_equivalent'])} Stück rechnerisch · "
                     f"Rundungsvorschlag {status['quantity_to_process']} Stück"
            )
        else:
            self.active_details.configure(
                text=f"Arbeitseinsatz #{status['id']} · {status['quantity_to_process']} Stück · "
                     f"{seconds_to_minutes(status['seconds_per_piece'])} min/Stück"
            )
        overdue = status["time_state"] == "ueberzogen"
        self.countdown_caption.configure(
            text="RÜCKMELDUNG ÜBERFÄLLIG" if overdue else "BIS GEPLANTER RÜCKMELDUNG"
        )
        self.countdown.configure(
            text=("+" if overdue else "") + format_duration(status["time_seconds"]),
            style="Danger.TLabel" if overdue else "Countdown.TLabel",
        )
        started = datetime.fromisoformat(status["reported_started_at"])
        target = datetime.fromisoformat(status["target_end"])
        total_clock_seconds = max((target - started).total_seconds(), 1)
        elapsed_clock_seconds = max((datetime.now().astimezone().replace(tzinfo=None) - started).total_seconds(), 0)
        self.work_progress.configure(value=min(elapsed_clock_seconds / total_clock_seconds * 100, 100))
        extensions = self.database.session_extensions(int(status["id"]))
        self.target_label.configure(
            text=(
                f"Geplante Abmeldezeit für {format_duration(status['credit_planned_seconds'])} Guthabenzeit: "
                if is_credit else
                f"Geplante Rückmeldezeit für {status['quantity_to_process']} Stück: "
            ) + f"{display_time(status['target_end'])}"
            + (f" · {len(extensions)}× verlängert" if extensions else "")
        )
        if is_credit:
            self.forecast_label.configure(
                text=f"Verfügbares Guthaben vor dieser Rückmeldung: {status['credit_quantity']} Stück\n"
                     f"Du entscheidest beim Abmelden über die tatsächlich gemeldete ganze Stückzahl."
            )
            self.order_remaining_label.configure(
                text=f"Guthabenwert: {status['credit_quantity']} Stück · "
                     f"{seconds_to_minutes(status['credit_quantity'] * status['seconds_per_piece'])} Minuten"
            )
            if not self.finish_reported_quantity.get().strip():
                self._set_entry(
                    self.finish_reported_quantity, str(status["quantity_to_process"])
                )
        elif "pieces_until_shift_end" in status:
            next_piece_text = ""
            if status["next_piece_finish"] is not None:
                next_piece_text = (
                    f"\nEin weiteres Stück wäre um {status['next_piece_finish']:%H:%M} fertig "
                    f"({status['next_piece_overtime_seconds'] // 60} Min. nach Schichtende)."
                )
            self.forecast_label.configure(
                text=f"Schichtprognose ab Anmeldung: "
                     f"{format_piece_equivalent(status['target_piece_equivalent'])} Stück\n"
                     f"Davon vollständig: {status['pieces_until_shift_end']} Stück"
                     f"{next_piece_text}"
            )
        elif not is_credit:
            self.forecast_label.configure(text="Keine Schicht für die Reststückprognose gewählt.")
        if not is_credit and "order_open_quantity" in status:
            remaining = format_duration(status["order_open_seconds"])
            extra = format_duration(status["beyond_shift_seconds"])
            self.order_remaining_label.configure(
                text=f"Gesamtauftrag noch nicht rückgemeldet: {status['order_open_quantity']} Stück · "
                     f"{remaining} Vorgabezeit\n"
                     f"Davon außerhalb der aktuellen Schichtkapazität: {extra}"
            )
        if overdue and self.notified_session_id != status["id"]:
            self.notified_session_id = int(status["id"])
            self.bell()
            messagebox.showwarning(
                "Geplante Rückmeldezeit erreicht",
                "Die geplante Rückmeldezeit für diesen Arbeitseinsatz ist erreicht. "
                "Bitte Stückzahl rückmelden oder die Überziehung weiterlaufen lassen.",
                parent=self,
            )

    def refresh_history(self) -> None:
        self.history_tree.delete(*self.history_tree.get_children())
        status = self.history_status.get() if hasattr(self, "history_status") else "Alle"
        search = self.history_search.get() if hasattr(self, "history_search") else ""
        for item in self.database.history(
            limit=500,
            search=search,
            status="" if status == "Alle" else status,
        ):
            start = display_time(item["reported_started_at"])
            end = display_time(item["reported_ended_at"])
            performance = calculate_performance(item)
            actual_quantity = (
                item["completed_quantity"] if item["completed_quantity"] is not None else "–"
            )
            reported_quantity = (
                item["reported_quantity"] if item["reported_quantity"] is not None else "–"
            )
            self.history_tree.insert(
                "", "end", iid=str(item["id"]), values=(
                    start[:10], item["order_number"], item["die_number"], item["operation"],
                    f"{start[11:]} – {end[11:] if end != '–' else 'offen'}",
                    f"{actual_quantity}/{reported_quantity}/{item['quantity_to_process']}",
                    format_time_performance(performance),
                    format_quantity_performance(performance),
                    item["status"],
                )
            )

    def reset_history_filter(self) -> None:
        self.history_search.delete(0, tk.END)
        self.history_status.set("Alle")
        self.refresh_history()

    def show_history_details(self, _event=None) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        session = self.database.get_session(int(selected[0]))
        if session is None:
            return
        performance = calculate_performance(session)
        credit_change = (
            int(session["completed_quantity"] or 0) - int(session["reported_quantity"] or 0)
        )
        messagebox.showinfo(
            "Meldungsdetails",
            f"Auftrag: {session['order_number']}\n"
            f"Gesenk / Arbeitsgang: {session['die_number']} / {session['operation']}\n"
            f"Anmeldung: {display_time(session['reported_started_at'])}\n"
            f"Geplante Rückmeldung: {display_time(session['target_end'])}\n"
            f"Abmeldung: {display_time(session['reported_ended_at'])}\n"
            f"Tatsächlich bearbeitet: {session['completed_quantity'] if session['completed_quantity'] is not None else '–'}\n"
            f"Betrieblich rückgemeldet: {session['reported_quantity'] if session['reported_quantity'] is not None else '–'}\n"
            f"Guthabenänderung: {credit_change:+d} Stück\n"
            f"Zeitabweichung: {format_time_performance(performance)}\n"
            f"Stückabweichung: {format_quantity_performance(performance)}\n"
            f"Notiz: {session['note'] or '–'}",
            parent=self,
        )

    def _selected_history_session(self) -> dict | None:
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showinfo("Keine Auswahl", "Bitte zuerst eine Rückmeldung auswählen.", parent=self)
            return None
        return self.database.get_session(int(selected[0]))

    def edit_history_order(self) -> None:
        session = self._selected_history_session()
        if session is not None:
            self.open_order_editor(int(session["order_id"]))

    def void_history_entry(self) -> None:
        session = self._selected_history_session()
        if session is None:
            return
        reason = simpledialog.askstring(
            "Rückmeldung stornieren",
            "Warum soll diese Rückmeldung storniert werden?",
            parent=self,
        )
        if reason is None:
            return
        try:
            self.database.void_session(int(session["id"]), reason=reason)
        except ValueError as error:
            messagebox.showerror("Stornierung nicht möglich", str(error), parent=self)
            return
        self.load_persisted_shift_plan()
        self.refresh_all()

    def open_history_trash(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Stornierte Rückmeldungen")
        dialog.geometry("880x420")
        dialog.transient(self)
        body = ttk.Frame(dialog, padding=14); body.pack(fill="both", expand=True)
        ttk.Label(body, text="Storno-Papierkorb", style="Title.TLabel").pack(anchor="w")
        tree = ttk.Treeview(
            body, columns=("id", "date", "order", "die", "actual", "reported"),
            show="headings", height=12,
        )
        for column, heading, width in zip(
            ("id", "date", "order", "die", "actual", "reported"),
            ("ID", "Datum", "Auftrag", "Gesenk", "Bearbeitet", "Rückgemeldet"),
            (50, 130, 220, 100, 110, 120),
        ):
            tree.heading(column, text=heading); tree.column(column, width=width, anchor="center")
        tree.pack(fill="both", expand=True, pady=10)

        def refresh() -> None:
            tree.delete(*tree.get_children())
            for item in self.database.history(limit=10000, status="storniert"):
                tree.insert("", "end", iid=str(item["id"]), values=(
                    item["id"], display_time(item["reported_started_at"]), item["order_number"],
                    item["die_number"], item["completed_quantity"], item["reported_quantity"],
                ))

        def selected_id() -> int:
            if not tree.selection():
                raise ValueError("Bitte eine stornierte Rückmeldung auswählen.")
            return int(tree.selection()[0])

        def restore() -> None:
            try:
                self.database.restore_voided_session(selected_id())
            except ValueError as error:
                messagebox.showerror("Wiederherstellen nicht möglich", str(error), parent=dialog); return
            refresh(); self.refresh_all()

        def delete() -> None:
            try:
                session_id = selected_id()
                if not messagebox.askyesno(
                    "Endgültig löschen", "Diese stornierte Rückmeldung unwiderruflich löschen?",
                    icon="warning", parent=dialog,
                ):
                    return
                self.database.permanently_delete_voided_session(session_id)
            except ValueError as error:
                messagebox.showerror("Löschen nicht möglich", str(error), parent=dialog); return
            refresh(); self.refresh_all()

        actions = ttk.Frame(body); actions.pack(fill="x")
        ttk.Button(actions, text="Wiederherstellen", command=restore).pack(side="left")
        ttk.Button(actions, text="Endgültig löschen", command=delete).pack(side="right")
        refresh()

    def edit_history_entry(self) -> None:
        session = self._selected_history_session()
        if session is None:
            return
        if session["status"] != "abgeschlossen":
            messagebox.showerror(
                "Korrektur nicht möglich", "Nur abgeschlossene Rückmeldungen können korrigiert werden.",
                parent=self,
            )
            return
        dialog = tk.Toplevel(self)
        dialog.title(f"Rückmeldung #{session['id']} korrigieren")
        dialog.transient(self)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"{session['order_number']} · {session['die_number']} / {session['operation']}",
            style="Title.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        fields = (
            ("Anmeldezeit", datetime.fromisoformat(session["reported_started_at"]).strftime("%Y-%m-%d %H:%M")),
            ("Abmeldezeit", datetime.fromisoformat(session["reported_ended_at"]).strftime("%Y-%m-%d %H:%M")),
            ("Tatsächlich bearbeitet", str(session["completed_quantity"] or 0)),
            ("Betrieblich rückgemeldet", str(session["reported_quantity"] or 0)),
            ("Notiz", session["note"] or ""),
            ("Korrekturgrund", ""),
        )
        entries: list[ttk.Entry] = []
        for row, (label, value) in enumerate(fields, start=1):
            ttk.Label(frame, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            entry = ttk.Entry(frame, width=48)
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entries.append(entry)
        ttk.Label(
            frame,
            text="Jede Änderung bleibt mit altem Wert, neuem Wert und Grund im Protokoll erhalten.",
            style="Muted.TLabel",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 6))

        def save() -> None:
            try:
                start = parse_datetime(entries[0].get())
                end = parse_datetime(entries[1].get())
                actual = int(entries[2].get())
                reported = int(entries[3].get())
                reason = entries[5].get().strip()
                if not messagebox.askyesno(
                    "Korrektur bestätigen",
                    "Diese Rückmeldung wirklich ändern? Die Änderung wird dauerhaft protokolliert.",
                    parent=dialog,
                ):
                    return
                self.database.correct_session(
                    int(session["id"]), reported_started_at=start, reported_ended_at=end,
                    completed_quantity=actual, reported_quantity=reported,
                    note=entries[4].get(), reason=reason,
                )
            except (ValueError, TypeError) as error:
                messagebox.showerror("Korrektur nicht gespeichert", str(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh_all()
            messagebox.showinfo("Korrektur gespeichert", "Mengen, Guthaben und Abweichungen wurden neu berechnet.", parent=self)

        ttk.Button(frame, text="KORREKTUR SPEICHERN", style="Primary.TButton", command=save).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )
        frame.columnconfigure(1, weight=1)
        dialog.wait_window()

    def show_session_corrections(self) -> None:
        session = self._selected_history_session()
        if session is None:
            return
        corrections = self.database.corrections("session", int(session["id"]))
        if not corrections:
            messagebox.showinfo("Korrekturprotokoll", "Diese Rückmeldung wurde noch nicht korrigiert.", parent=self)
            return
        lines = []
        for item in corrections:
            changed = display_time(item["changed_at"])
            lines.append(
                f"{changed} · {item['field_name']}\n"
                f"  vorher: {json.loads(item['old_value']) if item['old_value'] else '–'}\n"
                f"  nachher: {json.loads(item['new_value']) if item['new_value'] else '–'}\n"
                f"  Grund: {item['reason']}"
            )
        messagebox.showinfo("Korrekturprotokoll", "\n\n".join(lines), parent=self)

    def _build_settings(self) -> None:
        ttk.Label(self.settings_tab, text="Schichten und Pausen", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            self.settings_tab,
            text=(
                "Diese Zeiten gelten für Prognosen und Rückmeldungen. Die Uhr läuft während "
                "der Pause weiter; WerkMate zieht sie nur bei der Sollzeitberechnung ab."
            ),
            style="Muted.TLabel",
            wraplength=850,
        ).pack(anchor="w", pady=(4, 18))
        frame = ttk.LabelFrame(self.settings_tab, text="Arbeitszeitmodell", padding=12)
        frame.pack(fill="x")
        for column, text_value in enumerate(("Schicht", "Beginn", "Ende", "Pause von", "Pause bis")):
            ttk.Label(frame, text=text_value).grid(row=0, column=column, padx=8, pady=4)
        self.shift_setting_entries: dict[int, list[ttk.Entry]] = {}
        for row, item in enumerate(self.database.shift_settings(), start=1):
            number = int(item["shift_number"])
            ttk.Label(frame, text=f"Schicht {number}").grid(row=row, column=0, padx=8, pady=6)
            entries = []
            for column, key in enumerate(
                ("start_time", "end_time", "break_start", "break_end"), start=1
            ):
                entry = ttk.Entry(frame, width=12, justify="center")
                entry.insert(0, item[key])
                entry.grid(row=row, column=column, padx=8, pady=6)
                entries.append(entry)
            self.shift_setting_entries[number] = entries
        buttons = ttk.Frame(self.settings_tab)
        buttons.pack(fill="x", pady=12)
        ttk.Button(
            buttons, text="Standardzeiten einsetzen", command=self.reset_shift_settings_form
        ).pack(side="left")
        ttk.Button(
            buttons, text="EINSTELLUNGEN SPEICHERN", style="Primary.TButton",
            command=self.save_shift_settings,
        ).pack(side="right")
        ttk.Label(
            self.settings_tab,
            text="Zeitformat: HH:MM · Nachtschichten über Mitternacht werden automatisch erkannt.",
            style="Muted.TLabel",
        ).pack(anchor="w")
        data = ttk.LabelFrame(self.settings_tab, text="Datensicherheit und Export", padding=12)
        data.pack(fill="x", pady=(24, 0))
        ttk.Label(
            data,
            text="Sicherungen wiederherstellen oder Aufträge und Rückmeldungen als CSV ausgeben.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 10))
        data_buttons = ttk.Frame(data)
        data_buttons.pack(fill="x")
        ttk.Button(data_buttons, text="CSV-Dateien exportieren", command=self.export_csv).pack(
            side="left"
        )
        ttk.Button(
            data_buttons, text="Sicherung wiederherstellen", command=self.restore_database
        ).pack(side="left", padx=8)

    def reset_shift_settings_form(self) -> None:
        defaults = {
            1: ("05:45", "13:45", "08:45", "09:03"),
            2: ("13:45", "21:45", "17:45", "18:03"),
            3: ("21:45", "05:45", "01:45", "02:03"),
        }
        for number, values in defaults.items():
            for entry, value in zip(self.shift_setting_entries[number], values):
                self._set_entry(entry, value)

    def save_shift_settings(self) -> None:
        settings = []
        for number, entries in self.shift_setting_entries.items():
            settings.append({
                "shift_number": number,
                "start_time": entries[0].get().strip(),
                "end_time": entries[1].get().strip(),
                "break_start": entries[2].get().strip(),
                "break_end": entries[3].get().strip(),
            })
        try:
            self.database.save_shift_settings(settings)
        except ValueError as error:
            messagebox.showerror("Einstellungen nicht gespeichert", str(error), parent=self)
            return
        messagebox.showinfo(
            "Einstellungen gespeichert",
            "Die neuen Zeiten gelten für alle künftig gestarteten Arbeitseinsätze und Pläne.",
            parent=self,
        )

    def export_csv(self) -> None:
        destination = filedialog.askdirectory(parent=self, title="Ordner für CSV-Export auswählen")
        if not destination:
            return
        try:
            orders_path, history_path = self.database.export_csv(destination)
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror("Export fehlgeschlagen", str(error), parent=self)
            return
        messagebox.showinfo(
            "CSV-Export erstellt",
            f"Aufträge:\n{orders_path}\n\nRückmeldungen:\n{history_path}",
            parent=self,
        )

    def restore_database(self) -> None:
        source = filedialog.askopenfilename(
            parent=self,
            title="WerkMate-Sicherung auswählen",
            filetypes=(("WerkMate-Datenbank", "*.sqlite3"), ("Alle Dateien", "*.*")),
        )
        if not source:
            return
        if not messagebox.askyesno(
            "Sicherung wiederherstellen",
            "Der aktuelle Datenstand wird durch die gewählte Sicherung ersetzt.\n\n"
            "WerkMate legt vorher automatisch eine zusätzliche Sicherheitskopie an. Fortfahren?",
            parent=self,
        ):
            return
        safety_copy = self.database.path.with_name(
            f"werkmate-vor-wiederherstellung-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        )
        try:
            self.database.backup_to(safety_copy)
            self.database.restore_from(source)
        except (OSError, sqlite3.Error, ValueError) as error:
            messagebox.showerror(
                "Wiederherstellung fehlgeschlagen",
                f"{error}\n\nDer bisherige Stand wurde nicht bewusst verworfen.\n"
                f"Sicherheitskopie: {safety_copy}",
                parent=self,
            )
            return
        self.shift_plan_items.clear()
        self.shift_plan_results.clear()
        self.load_persisted_shift_plan()
        self.refresh_all()
        messagebox.showinfo(
            "Sicherung wiederhergestellt",
            f"Die Daten wurden übernommen.\n\nVorheriger Stand:\n{safety_copy}",
            parent=self,
        )

    def refresh_all(self) -> None:
        self.refresh_orders()
        self.refresh_dashboard()
        self.refresh_analytics()
        self.refresh_catalog()
        self._refresh_die_suggestions()
        self._refresh_quick_dies()
        self.refresh_plan_orders()
        self.refresh_history()
        if hasattr(self, "plan_start_button"):
            self.plan_start_button.configure(
                state="disabled" if self.database.active_session() is not None else "normal"
            )

    def _tick(self) -> None:
        self.refresh_dashboard()
        self.after(1_000, self._tick)


def main() -> None:
    app = WerkMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
