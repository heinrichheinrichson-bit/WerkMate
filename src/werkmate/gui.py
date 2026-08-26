"""Einfache grafische PC-Oberfläche für den WerkMate-MVP."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .cli import default_database_path, format_duration, parse_datetime, warn_unusual_end
from .database import WerkMateDatabase
from .service import WerkMateService
from .timecalc import minutes_to_seconds, seconds_to_minutes


def local_now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def display_time(value: str | None) -> str:
    if not value:
        return "–"
    return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")


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
        self.orders_tab = ttk.Frame(self.tabs, padding=18)
        self.history_tab = ttk.Frame(self.tabs, padding=18)
        self.tabs.add(self.dashboard_tab, text="Laufender Auftrag")
        self.tabs.add(self.orders_tab, text="Aufträge")
        self.tabs.add(self.history_tab, text="Historie")

        self._build_dashboard()
        self._build_orders()
        self._build_history()

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

        finish = ttk.LabelFrame(self.dashboard_tab, text="Arbeitseinsatz rückmelden", padding=14)
        finish.pack(fill="x", pady=(20, 0))
        ttk.Label(finish, text="Fertige Stück:").grid(row=0, column=0, sticky="w")
        self.finish_quantity = ttk.Entry(finish, width=10)
        self.finish_quantity.grid(row=0, column=1, padx=(8, 24), sticky="w")
        ttk.Label(finish, text="Abmeldezeit:").grid(row=0, column=2, sticky="w")
        self.finish_time = ttk.Entry(finish, width=19)
        self.finish_time.grid(row=0, column=3, padx=8, sticky="w")
        ttk.Button(finish, text="Aktuelle Zeit", command=self._fill_finish_now).grid(row=0, column=4)
        ttk.Label(finish, text="Notiz:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.finish_note = ttk.Entry(finish)
        self.finish_note.grid(row=1, column=1, columnspan=4, sticky="ew", padx=(8, 0), pady=(12, 0))
        ttk.Button(
            finish, text="Rückmeldung speichern", style="Primary.TButton",
            command=self.finish_active,
        ).grid(row=2, column=0, columnspan=5, sticky="ew", pady=(16, 0))
        finish.columnconfigure(3, weight=1)

    def _build_orders(self) -> None:
        form = ttk.LabelFrame(self.orders_tab, text="Neuen Auftrag anlegen", padding=12)
        form.pack(fill="x")
        labels = ("Auftragsnummer", "Gesenknummer", "Arbeitsgang", "Menge", "min/Stück")
        self.order_entries: list[ttk.Entry] = []
        for column, label in enumerate(labels):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=4)
            entry = ttk.Entry(form, width=16)
            entry.grid(row=1, column=column, sticky="ew", padx=4, pady=(3, 8))
            self.order_entries.append(entry)
            form.columnconfigure(column, weight=1)
        ttk.Label(form, text="Auftragsnotiz").grid(row=2, column=0, sticky="w", padx=4)
        self.order_note = ttk.Entry(form)
        self.order_note.grid(row=3, column=0, columnspan=4, sticky="ew", padx=4)
        ttk.Button(form, text="Auftrag anlegen", command=self.create_order).grid(
            row=3, column=4, sticky="ew", padx=4
        )

        list_frame = ttk.LabelFrame(self.orders_tab, text="Gespeicherte Aufträge", padding=10)
        list_frame.pack(fill="both", expand=True, pady=14)
        columns = ("id", "order", "die", "operation", "quantity", "time", "status")
        self.orders_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        headings = ("ID", "Auftrag", "Gesenk", "AG", "Offen/Gesamt", "Vorgabe", "Status")
        widths = (45, 130, 100, 80, 110, 100, 150)
        for column, heading, width in zip(columns, headings, widths):
            self.orders_tree.heading(column, text=heading)
            self.orders_tree.column(column, width=width, anchor="center")
        self.orders_tree.pack(fill="both", expand=True)

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
        start.columnconfigure(7, weight=1)
        self._fill_start_now()

    def _build_history(self) -> None:
        columns = ("date", "order", "die", "operation", "times", "quantity", "status")
        self.history_tree = ttk.Treeview(
            self.history_tab, columns=columns, show="headings", height=18
        )
        headings = ("Datum", "Auftrag", "Gesenk", "AG", "An-/Abmeldung", "Stück", "Status")
        widths = (90, 115, 90, 70, 245, 60, 130)
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
        self.refresh_orders()
        messagebox.showinfo("Gespeichert", "Der Auftrag wurde lokal angelegt.", parent=self)

    def selected_order_id(self) -> int:
        selected = self.orders_tree.selection()
        if not selected:
            raise ValueError("Bitte zuerst einen Auftrag in der Liste auswählen.")
        return int(self.orders_tree.item(selected[0], "values")[0])

    def start_selected(self) -> None:
        try:
            order_id = self.selected_order_id()
            shift = int(self.shift_number.get()) if self.shift_number.get() else None
            self.service.start_work(
                order_id=order_id,
                quantity=int(self.start_quantity.get()),
                reported_start=self._entry_datetime(self.start_time),
                shift_number=shift,
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Start nicht möglich", str(error), parent=self)
            return
        self.notified_session_id = None
        self.tabs.select(self.dashboard_tab)
        self.refresh_all()

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
            self.service.finish_work(
                int(session["id"]),
                completed_quantity=int(self.finish_quantity.get()),
                reported_end=reported_end,
                note=self.finish_note.get(),
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Rückmeldung nicht möglich", str(error), parent=self)
            return
        self.finish_quantity.delete(0, tk.END)
        self.finish_note.delete(0, tk.END)
        self.refresh_all()
        messagebox.showinfo(
            "Rückmeldung gespeichert",
            "Stückzahl, Abmeldezeit und Notiz wurden in der Historie gespeichert.",
            parent=self,
        )

    def refresh_orders(self) -> None:
        self.orders_tree.delete(*self.orders_tree.get_children())
        for order in self.database.list_orders():
            self.orders_tree.insert(
                "", "end", values=(
                    order["id"], order["order_number"], order["die_number"],
                    order["operation"], f"{order['open_quantity']}/{order['original_quantity']}",
                    f"{seconds_to_minutes(order['seconds_per_piece'])} min", order["status"],
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
            return

        self.active_title.configure(
            text=f"{status['order_number']} · Ges. {status['die_number']} · {status['operation']}"
        )
        self.active_details.configure(
            text=f"Einsatz #{status['id']} · {status['quantity_to_process']} Stück · "
                 f"{seconds_to_minutes(status['seconds_per_piece'])} min/Stück"
        )
        overdue = status["time_state"] == "ueberzogen"
        self.countdown_caption.configure(text="AUFTRAG ÜBERZOGEN" if overdue else "VERBLEIBEND")
        self.countdown.configure(
            text=("+" if overdue else "") + format_duration(status["time_seconds"]),
            style="Danger.TLabel" if overdue else "Countdown.TLabel",
        )
        self.target_label.configure(text=f"Soll-Ende: {display_time(status['target_end'])}")
        if "pieces_until_shift_end" in status:
            self.forecast_label.configure(
                text=f"Bis Schichtende laut Vorgabe: {status['pieces_until_shift_end']} vollständige Stück\n"
                     f"Nächstes Stück: +{format_duration(status['next_piece_overtime_seconds'])} Überzeit"
            )
        else:
            self.forecast_label.configure(text="Keine Schicht für die Reststückprognose gewählt.")
        if overdue and self.notified_session_id != status["id"]:
            self.notified_session_id = int(status["id"])
            self.bell()
            messagebox.showwarning(
                "Sollzeit erreicht",
                "Die Sollzeit ist abgelaufen. Bitte Auftrag rückmelden oder die Überziehung weiterlaufen lassen.",
                parent=self,
            )

    def refresh_history(self) -> None:
        self.history_tree.delete(*self.history_tree.get_children())
        for item in self.database.history(limit=500):
            start = display_time(item["reported_started_at"])
            end = display_time(item["reported_ended_at"])
            self.history_tree.insert(
                "", "end", iid=str(item["id"]), values=(
                    start[:10], item["order_number"], item["die_number"], item["operation"],
                    f"{start[11:]} – {end[11:] if end != '–' else 'offen'}",
                    item["completed_quantity"] if item["completed_quantity"] is not None else "–",
                    item["status"],
                )
            )

    def show_history_details(self, _event=None) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        session = self.database.get_session(int(selected[0]))
        if session is None:
            return
        messagebox.showinfo(
            "Meldungsdetails",
            f"Auftrag: {session['order_number']}\n"
            f"Gesenk / Arbeitsgang: {session['die_number']} / {session['operation']}\n"
            f"Anmeldung: {display_time(session['reported_started_at'])}\n"
            f"Soll-Ende: {display_time(session['target_end'])}\n"
            f"Abmeldung: {display_time(session['reported_ended_at'])}\n"
            f"Fertig gemeldet: {session['completed_quantity'] if session['completed_quantity'] is not None else '–'}\n"
            f"Notiz: {session['note'] or '–'}",
            parent=self,
        )

    def refresh_all(self) -> None:
        self.refresh_orders()
        self.refresh_dashboard()
        self.refresh_history()

    def _tick(self) -> None:
        self.refresh_dashboard()
        self.after(1_000, self._tick)


def main() -> None:
    app = WerkMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
