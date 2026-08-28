"""Einfacher WerkMate-Schichtrechner ohne Auftragsverwaltung."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk

from .calculator import calculate_shift_requirement
from .cli import default_database_path
from .database import WerkMateDatabase
from .service import WerkMateService
from .timecalc import minutes_to_seconds, seconds_to_minutes


def local_now() -> datetime:
    return datetime.now().astimezone().replace(tzinfo=None, second=0, microsecond=0)


@dataclass
class PlanJob:
    die: str
    quantity: int
    seconds_per_piece: int


class SimpleWerkMateApp(tk.Tk):
    VERSION = "Simple 0.3"

    def __init__(self, database_path=None) -> None:
        super().__init__()
        self.title(f"WerkMate · {self.VERSION}")
        self.geometry("860x820")
        self.minsize(720, 680)
        self.database = WerkMateDatabase(database_path or default_database_path())
        self.service = WerkMateService(self.database)
        self.plan_date = local_now().date()
        self.jobs: list[PlanJob] = []
        self._style()
        self._ui()
        self._load_catalog()

    def _style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.configure(background="#f4f6f8")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8", font=("Segoe UI", 11))
        style.configure("Muted.TLabel", foreground="#667085")
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground="#101828")
        style.configure("Result.TLabel", font=("Segoe UI", 22, "bold"), foreground="#175cd3")
        style.configure("Card.TLabelframe", background="#ffffff", bordercolor="#d0d5dd")
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 12, "bold"), padding=(16, 12), background="#2f6fed", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#175cd3")])
        style.configure("TEntry", padding=8)
        style.configure("TCombobox", padding=8)

    def _ui(self) -> None:
        body = ttk.Frame(self, padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Meine Schicht planen", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="Arbeiten eintragen – WerkMate verteilt die Stück bis Schichtende.", style="Muted.TLabel").pack(anchor="w", pady=(3, 16))

        shift = ttk.LabelFrame(body, text="SCHICHT", style="Card.TLabelframe", padding=14)
        shift.pack(fill="x")
        shift.columnconfigure(0, weight=2)
        shift.columnconfigure(1, weight=1)
        ttk.Label(shift, text="Schicht").grid(row=0, column=0, sticky="w")
        self.shift_options = self._shift_labels()
        self.shift_entry = ttk.Combobox(shift, values=tuple(self.shift_options.values()), state="readonly")
        self.shift_entry.set(self.shift_options[self._current_shift(local_now())])
        self.shift_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        self.shift_entry.bind("<<ComboboxSelected>>", self._shift_selected)
        ttk.Label(shift, text="Beginn der ersten Arbeit").grid(row=0, column=1, sticky="w")
        self.start_entry = ttk.Entry(shift)
        self.start_entry.insert(0, local_now().strftime("%H:%M"))
        self.start_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.date_hint = ttk.Label(shift, style="Muted.TLabel")
        self.date_hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(7, 0))
        self._date_hint()

        form = ttk.LabelFrame(body, text="ARBEIT HINZUFÜGEN", style="Card.TLabelframe", padding=14)
        form.pack(fill="x", pady=(12, 0))
        form.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(form, text="Gesenknummer (optional)").grid(row=0, column=0, sticky="w")
        self.die_entry = ttk.Combobox(form)
        self.die_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 10))
        self.die_entry.bind("<<ComboboxSelected>>", self._catalog_selected)
        ttk.Label(form, text="Gesamtstück").grid(row=0, column=1, sticky="w")
        self.quantity_entry = ttk.Entry(form)
        self.quantity_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(4, 10))
        ttk.Label(form, text="Stückzeit in Minuten").grid(row=0, column=2, sticky="w")
        self.piece_time_entry = ttk.Entry(form)
        self.piece_time_entry.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(4, 10))
        ttk.Label(form, text="Alternativ: Gesamtzeit in Minuten").grid(row=2, column=0, sticky="w")
        self.total_time_entry = ttk.Entry(form)
        self.total_time_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        ttk.Button(form, text="ARBEIT HINZUFÜGEN", command=self.add_job).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(4, 0))

        plan = ttk.LabelFrame(body, text="REIHENFOLGE", style="Card.TLabelframe", padding=12)
        plan.pack(fill="x", pady=(12, 0))
        self.job_tree = ttk.Treeview(plan, columns=("pos", "die", "quantity", "time"), show="headings", height=4)
        for key, title, width in (("pos", "Nr.", 45), ("die", "Gesenk", 220), ("quantity", "Gesamtstück", 110), ("time", "min/Stück", 110)):
            self.job_tree.heading(key, text=title)
            self.job_tree.column(key, width=width, anchor="w" if key == "die" else "center")
        self.job_tree.pack(fill="x")
        controls = ttk.Frame(plan)
        controls.pack(fill="x", pady=(8, 0))
        ttk.Button(controls, text="▲ Hoch", command=lambda: self.move_job(-1)).pack(side="left")
        ttk.Button(controls, text="▼ Runter", command=lambda: self.move_job(1)).pack(side="left", padx=6)
        ttk.Button(controls, text="Entfernen", command=self.remove_job).pack(side="left")
        ttk.Button(controls, text="Plan leeren", command=self.clear_jobs).pack(side="right")

        ttk.Button(body, text="SCHICHT BERECHNEN", style="Primary.TButton", command=self.calculate).pack(fill="x", pady=12)
        result = ttk.LabelFrame(body, text="SOLL-ABLAUF", style="Card.TLabelframe", padding=16)
        result.pack(fill="both", expand=True)
        self.main_result = ttk.Label(result, text="Noch keine Arbeiten geplant", style="Result.TLabel")
        self.main_result.pack(anchor="w")
        self.exact_result = ttk.Label(result, style="Muted.TLabel")
        self.exact_result.pack(anchor="w", pady=(3, 12))
        self.result_lines = ttk.Label(result, justify="left")
        self.result_lines.pack(anchor="w")

    def _shift_labels(self) -> dict[int, str]:
        names = {1: "Frühschicht", 2: "Spätschicht", 3: "Nachtschicht"}
        return {int(x["shift_number"]): f"{names[int(x['shift_number'])]} · {x['start_time']}–{x['end_time']}" for x in self.database.shift_settings()}

    def _current_shift(self, now: datetime) -> int:
        for item in self.database.shift_settings():
            start = datetime.strptime(item["start_time"], "%H:%M").time()
            end = datetime.strptime(item["end_time"], "%H:%M").time()
            if start <= now.time() < end if start < end else now.time() >= start or now.time() < end:
                return int(item["shift_number"])
        return 1

    def _selected_shift(self) -> int:
        for number, label in self.shift_options.items():
            if self.shift_entry.get() == label:
                return number
        raise ValueError("Bitte eine Schicht auswählen.")

    def _shift_selected(self, _event=None) -> None:
        setting = next(x for x in self.database.shift_settings() if int(x["shift_number"]) == self._selected_shift())
        now = local_now()
        candidate = datetime.combine(now.date(), datetime.strptime(setting["start_time"], "%H:%M").time())
        if candidate < now:
            candidate += timedelta(days=1)
        self.plan_date = candidate.date()
        self._replace(self.start_entry, candidate.strftime("%H:%M"))
        self._date_hint()

    def _date_hint(self) -> None:
        today = local_now().date()
        name = "heute" if self.plan_date == today else "morgen" if self.plan_date == today + timedelta(days=1) else self.plan_date.strftime("%d.%m.%Y")
        self.date_hint.configure(text=f"Geplant für {name}. Feste Pausen werden berücksichtigt.")

    def _load_catalog(self) -> None:
        self.die_entry.configure(values=sorted({x["die_number"] for x in self.database.list_catalog()}))

    def _catalog_selected(self, _event=None) -> None:
        times = {int(x["seconds_per_piece"]) for x in self.database.standards_for_die(self.die_entry.get().strip())}
        if len(times) == 1:
            self._replace(self.piece_time_entry, str(seconds_to_minutes(times.pop())).replace(".", ","))

    @staticmethod
    def _replace(entry: ttk.Entry, value: str) -> None:
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def _piece_seconds(self, quantity: int) -> int:
        if self.piece_time_entry.get().strip():
            return minutes_to_seconds(self.piece_time_entry.get())
        if self.total_time_entry.get().strip():
            return max(minutes_to_seconds(self.total_time_entry.get()) // quantity, 1)
        die = self.die_entry.get().strip()
        times = {int(x["seconds_per_piece"]) for x in self.database.standards_for_die(die)} if die else set()
        if len(times) == 1:
            return times.pop()
        if len(times) > 1:
            raise ValueError("Für dieses Gesenk gibt es mehrere Stückzeiten. Bitte Stückzeit eingeben.")
        raise ValueError("Bitte Stückzeit oder Gesamtzeit eingeben.")

    def add_job(self) -> None:
        try:
            quantity = int(self.quantity_entry.get().strip())
            if quantity <= 0:
                raise ValueError
            seconds = self._piece_seconds(quantity)
        except (ValueError, TypeError) as error:
            messagebox.showerror("Eingabe prüfen", str(error) or "Bitte eine gültige Gesamtstückzahl eingeben.", parent=self)
            return
        self.jobs.append(PlanJob(self.die_entry.get().strip() or f"Arbeit {len(self.jobs) + 1}", quantity, seconds))
        self._refresh_jobs()
        for entry in (self.die_entry, self.quantity_entry, self.piece_time_entry, self.total_time_entry):
            self._replace(entry, "")
        self.die_entry.focus_set()

    def _refresh_jobs(self) -> None:
        self.job_tree.delete(*self.job_tree.get_children())
        for index, job in enumerate(self.jobs):
            self.job_tree.insert("", "end", iid=str(index), values=(index + 1, job.die, job.quantity, str(seconds_to_minutes(job.seconds_per_piece)).replace(".", ",")))

    def _selection(self) -> int | None:
        selected = self.job_tree.selection()
        return int(selected[0]) if selected else None

    def move_job(self, direction: int) -> None:
        index = self._selection()
        if index is None or not 0 <= index + direction < len(self.jobs):
            return
        self.jobs[index], self.jobs[index + direction] = self.jobs[index + direction], self.jobs[index]
        self._refresh_jobs()
        self.job_tree.selection_set(str(index + direction))

    def remove_job(self) -> None:
        index = self._selection()
        if index is not None:
            self.jobs.pop(index)
            self._refresh_jobs()

    def clear_jobs(self) -> None:
        self.jobs.clear()
        self._refresh_jobs()
        self.main_result.configure(text="Noch keine Arbeiten geplant")
        self.exact_result.configure(text="")
        self.result_lines.configure(text="")

    def calculate(self) -> None:
        if not self.jobs:
            messagebox.showinfo("Noch leer", "Bitte zuerst mindestens eine Arbeit hinzufügen.", parent=self)
            return
        try:
            start = datetime.combine(self.plan_date, datetime.strptime(self.start_entry.get().strip(), "%H:%M").time())
            shift = self.service.shift_for_start(self._selected_shift(), start)
            if start < shift.start or start >= shift.end:
                raise ValueError(f"Der Beginn {start:%H:%M} liegt nicht in der gewählten Schicht ({shift.start:%H:%M}–{shift.end:%H:%M}).")
        except ValueError as error:
            messagebox.showerror("Eingabe prüfen", str(error), parent=self)
            return
        cursor, scheduled, lines = start, 0, []
        for index, job in enumerate(self.jobs, 1):
            if cursor >= shift.end:
                lines.append(f"{index} · {job.die}: keine Schichtzeit mehr frei")
                continue
            result = calculate_shift_requirement(total_quantity=job.quantity, start=cursor, shift_end=shift.end, breaks=shift.breaks, seconds_per_piece=job.seconds_per_piece)
            exact = str(result.exact_pieces.quantize(Decimal("0.1"))).replace(".", ",")
            lines.append(f"{index} · {job.die}   {cursor:%H:%M} → {result.planned_end:%H:%M}\n    {result.complete_pieces} ganze Stück ({exact} rechnerisch) · danach {result.remaining_pieces} offen")
            scheduled += result.complete_pieces
            cursor = result.planned_end
            if result.remaining_pieces:
                for later_index, later in enumerate(self.jobs[index:], index + 1):
                    lines.append(f"{later_index} · {later.die}: keine Schichtzeit mehr frei")
                break
        self.main_result.configure(text=f"{len(self.jobs)} Arbeiten · {scheduled} ganze Stück geplant")
        self.exact_result.configure(text=f"Soll-Ablauf {start:%H:%M}–{cursor:%H:%M} · Schichtende {shift.end:%H:%M}")
        self.result_lines.configure(text="\n\n".join(lines))


def main() -> None:
    SimpleWerkMateApp().mainloop()
