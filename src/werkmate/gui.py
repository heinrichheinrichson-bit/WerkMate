"""Einfache grafische PC-Oberfläche für den WerkMate-MVP."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .cli import default_database_path, format_duration, parse_datetime, warn_unusual_end
from .database import WerkMateDatabase
from .performance import (
    calculate_performance,
    format_quantity_performance,
    format_time_performance,
)
from .service import WerkMateService
from .timecalc import minutes_to_seconds, seconds_to_minutes


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
        self.plan_tab = ttk.Frame(self.tabs, padding=18)
        self.orders_tab = ttk.Frame(self.tabs, padding=18)
        self.catalog_tab = ttk.Frame(self.tabs, padding=18)
        self.history_tab = ttk.Frame(self.tabs, padding=18)
        self.settings_tab = ttk.Frame(self.tabs, padding=18)
        self.tabs.add(self.dashboard_tab, text="Laufender Auftrag")
        self.tabs.add(self.quick_tab, text="Schnellstart")
        self.tabs.add(self.plan_tab, text="Schichtplan")
        self.tabs.add(self.orders_tab, text="Aufträge")
        self.tabs.add(self.catalog_tab, text="Gesenk-Katalog")
        self.tabs.add(self.history_tab, text="Historie")
        self.tabs.add(self.settings_tab, text="Einstellungen")

        self._build_dashboard()
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
        self.target_label = ttk.Label(self.dashboard_tab, text="")
        self.target_label.pack()
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
        ttk.Label(self.plan_tab, text="Aufträge und Guthaben zusammen planen", style="Title.TLabel").pack(
            anchor="w"
        )
        settings = ttk.Frame(self.plan_tab)
        settings.pack(fill="x", pady=(12, 8))
        ttk.Label(settings, text="Planstart:").pack(side="left")
        self.plan_start = ttk.Entry(settings, width=20)
        self.plan_start.insert(0, local_now().strftime("%Y-%m-%d %H:%M"))
        self.plan_start.pack(side="left", padx=(6, 16))
        ttk.Label(settings, text="Schicht:").pack(side="left")
        self.plan_shift = ttk.Combobox(settings, values=("1", "2", "3"), state="readonly", width=6)
        self.plan_shift.set(str(self._current_shift_number(local_now())))
        self.plan_shift.pack(side="left", padx=6)

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
                "Offene Stück fest",
                "Restschicht mit Auftrag füllen",
                "Guthaben nach Stück",
                "Guthaben nach Minuten",
            ),
            state="readonly",
            width=30,
        )
        self.plan_mode.set("Offene Stück fest")
        self.plan_mode.grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Label(add, text="Stück/Minuten:").grid(row=0, column=2, sticky="w")
        self.plan_value = ttk.Entry(add, width=15)
        self.plan_value.grid(row=1, column=2, sticky="ew", padx=8)
        ttk.Button(add, text="Zum Plan hinzufügen", command=self.add_shift_plan_item).grid(
            row=1, column=3, sticky="ew", padx=(8, 0)
        )
        add.columnconfigure(0, weight=2)
        add.columnconfigure(1, weight=1)

        queue_frame = ttk.LabelFrame(self.plan_tab, text="Reihenfolge", padding=8)
        queue_frame.pack(fill="x", pady=10)
        self.plan_queue = ttk.Treeview(
            queue_frame,
            columns=("pos", "order", "die", "mode", "value"),
            show="headings",
            height=5,
        )
        for column, heading, width in zip(
            ("pos", "order", "die", "mode", "value"),
            ("Pos.", "Auftrag", "Gesenk/AG", "Planungsart", "Vorgabe"),
            (45, 150, 130, 260, 120),
        ):
            self.plan_queue.heading(column, text=heading)
            self.plan_queue.column(column, width=width, anchor="center")
        self.plan_queue.pack(fill="x")
        queue_buttons = ttk.Frame(queue_frame)
        queue_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(queue_buttons, text="Ausgewählten entfernen", command=self.remove_shift_plan_item).pack(
            side="left"
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
        columns = ("pos", "order", "kind", "start", "end", "pieces", "equiv", "overtime")
        self.plan_result_tree = ttk.Treeview(
            result_frame, columns=columns, show="headings", height=7
        )
        for column, heading, width in zip(
            columns,
            ("Pos.", "Auftrag", "Art", "Start", "Ende", "ganze Stück", "rechnerisch", "Überzeit"),
            (45, 140, 90, 120, 120, 95, 100, 100),
        ):
            self.plan_result_tree.heading(column, text=heading)
            self.plan_result_tree.column(column, width=width, anchor="center")
        self.plan_result_tree.pack(fill="both", expand=True)
        ttk.Button(
            result_frame,
            text="Ersten Planpunkt starten",
            style="Primary.TButton",
            command=self.start_first_shift_plan_item,
        ).pack(fill="x", pady=(8, 0))

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
            "Offene Stück fest": "work_fixed",
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
                )
            )

    def remove_shift_plan_item(self) -> None:
        selected = self.plan_queue.selection()
        if not selected:
            return
        del self.shift_plan_items[int(selected[0])]
        self.refresh_shift_plan_queue()
        self.plan_result_tree.delete(*self.plan_result_tree.get_children())

    def clear_shift_plan(self) -> None:
        self.shift_plan_items.clear()
        self.shift_plan_results.clear()
        self.database.discard_shift_plan()
        self.plan_saved_label.configure(text="")
        self.refresh_shift_plan_queue()
        self.plan_result_tree.delete(*self.plan_result_tree.get_children())

    def calculate_shift_plan(self, persist: bool = True) -> None:
        self.shift_plan_results = []
        try:
            self.shift_plan_results = self.service.plan_sequence(
                items=self.shift_plan_items,
                reported_start=parse_datetime(self.plan_start.get()),
                shift_number=int(self.plan_shift.get()),
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Planung nicht möglich", str(error), parent=self)
            return
        if persist:
            try:
                self.database.save_shift_plan(
                    reported_start=parse_datetime(self.plan_start.get()),
                    shift_number=int(self.plan_shift.get()),
                    items=self.shift_plan_items,
                )
                self.load_persisted_shift_plan(recalculate=False)
                self.plan_saved_label.configure(text="✓ lokal gespeichert")
            except ValueError as error:
                messagebox.showerror("Plan nicht gespeichert", str(error), parent=self)
                return
        self.plan_result_tree.delete(*self.plan_result_tree.get_children())
        for item in self.shift_plan_results:
            self.plan_result_tree.insert(
                "", "end", values=(
                    item["position"], item["order_number"],
                    "Guthaben" if item["kind"] == "credit" else "Bearbeitung",
                    item["planned_start"].strftime("%d.%m. %H:%M"),
                    item["planned_end"].strftime("%d.%m. %H:%M"),
                    item["quantity"], format_piece_equivalent(item["piece_equivalent"]),
                    f"{item['overtime_seconds'] // 60} min" if item["overtime_seconds"] else "–",
                )
            )

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
        self._set_entry(self.plan_start, item["planned_end"].strftime("%Y-%m-%d %H:%M"))
        self.refresh_shift_plan_queue()
        self.notified_session_id = None
        self.refresh_all()
        self.tabs.select(self.dashboard_tab)

    def load_persisted_shift_plan(self, *, recalculate: bool = True) -> None:
        plan = self.database.active_shift_plan()
        if plan is None:
            return
        labels = {
            "work_fixed": "Offene Stück fest",
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
            })
        self._set_entry(
            self.plan_start,
            datetime.fromisoformat(plan["reported_start"]).strftime("%Y-%m-%d %H:%M"),
        )
        self.plan_shift.set(str(plan["shift_number"]))
        self.refresh_shift_plan_queue()
        self.plan_saved_label.configure(text="✓ gespeicherten Plan geladen")
        if recalculate and self.shift_plan_items and self.database.active_session() is None:
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
        ttk.Button(self.history_tab, text="Historie aktualisieren", command=self.refresh_history).pack(
            anchor="e", pady=(10, 0)
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

    def edit_selected_order(self) -> None:
        try:
            order = self.database.get_order(self.selected_order_id())
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
            ("Auftragsnummer", order["order_number"], False),
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
                f"{next_item['planned_start']:%H:%M}.\nZum aktualisierten Schichtplan wechseln?"
                if next_item else "\n\nIm Schichtplan ist noch ein weiterer Auftrag vorgemerkt."
            )
            if messagebox.askyesno(title, message + next_text, parent=self):
                self.tabs.select(self.plan_tab)
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
            self.forecast_label.configure(text="")
            self.order_remaining_label.configure(text="")
            self.cancel_work_button.configure(state="disabled")
            return
        self.cancel_work_button.configure(state="normal")

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
        self.target_label.configure(
            text=(
                f"Geplante Abmeldezeit für {format_duration(status['credit_planned_seconds'])} Guthabenzeit: "
                if is_credit else
                f"Geplante Rückmeldezeit für {status['quantity_to_process']} Stück: "
            ) + f"{display_time(status['target_end'])}"
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

    def refresh_all(self) -> None:
        self.refresh_orders()
        self.refresh_dashboard()
        self.refresh_catalog()
        self._refresh_die_suggestions()
        self._refresh_quick_dies()
        self.refresh_plan_orders()
        self.refresh_history()

    def _tick(self) -> None:
        self.refresh_dashboard()
        self.after(1_000, self._tick)


def main() -> None:
    app = WerkMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
