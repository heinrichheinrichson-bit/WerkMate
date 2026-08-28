"""Einfacher WerkMate-Schichtrechner ohne Auftragsverwaltung."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from .calculator import calculate_shift_requirement
from .cli import default_database_path
from .database import WerkMateDatabase
from .service import WerkMateService
from .simple_plans import SimplePlanStore
from .simple_work import WorkModeWindow, WorkStep
from .timecalc import minutes_to_seconds, seconds_to_minutes


def local_now() -> datetime:
    return datetime.now().astimezone().replace(tzinfo=None, second=0, microsecond=0)


@dataclass
class PlanJob:
    die: str
    quantity: int
    seconds_per_piece: int


class SimpleWerkMateApp(tk.Tk):
    VERSION = "Simple 0.5"

    def __init__(self, database_path=None) -> None:
        super().__init__()
        self.title(f"WerkMate · {self.VERSION}")
        self.geometry("860x820")
        self.minsize(720, 680)
        db_path = Path(database_path or default_database_path())
        self.database = WerkMateDatabase(db_path)
        self.service = WerkMateService(self.database)
        self.plan_store = SimplePlanStore(db_path.with_name("simple_plans.json"))
        self.loaded_plan_name: str | None = None
        self.plan_date = local_now().date()
        self.jobs: list[PlanJob] = []
        self.calculated_steps: list[WorkStep] = []
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

        saved = ttk.Frame(body)
        saved.pack(fill="x", pady=(0, 10))
        ttk.Button(saved, text="Plan speichern", command=self.save_plan).pack(side="left")
        ttk.Button(saved, text="Gespeicherte Pläne", command=self.open_plan_manager).pack(side="left", padx=6)
        self.saved_hint = ttk.Label(saved, text="Noch nicht gespeichert", style="Muted.TLabel")
        self.saved_hint.pack(side="left", padx=8)

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
        ttk.Button(controls, text="Bearbeiten", command=self.edit_job).pack(side="left")
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
        self.work_button = ttk.Button(
            result, text="ARBEITSMODUS ÖFFNEN", style="Primary.TButton",
            command=self.open_work_mode, state="disabled",
        )
        self.work_button.pack(fill="x", side="bottom", pady=(16, 0))

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
        self._mark_changed()
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
        self._mark_changed()
        self._refresh_jobs()
        self.job_tree.selection_set(str(index + direction))

    def edit_job(self) -> None:
        index = self._selection()
        if index is None:
            messagebox.showinfo("Arbeit auswählen", "Bitte zuerst eine Arbeit in der Liste auswählen.", parent=self)
            return
        job = self.jobs[index]
        die = simpledialog.askstring("Arbeit bearbeiten", "Gesenknummer oder Bezeichnung:", initialvalue=job.die, parent=self)
        if die is None:
            return
        quantity_text = simpledialog.askstring("Arbeit bearbeiten", "Gesamtstück:", initialvalue=str(job.quantity), parent=self)
        if quantity_text is None:
            return
        minutes_text = simpledialog.askstring(
            "Arbeit bearbeiten", "Stückzeit in Minuten:",
            initialvalue=str(seconds_to_minutes(job.seconds_per_piece)).replace(".", ","), parent=self,
        )
        if minutes_text is None:
            return
        try:
            quantity = int(quantity_text.strip())
            seconds = minutes_to_seconds(minutes_text)
            if quantity <= 0 or seconds <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("Eingabe prüfen", "Gesamtstück und Stückzeit müssen größer als null sein.", parent=self)
            return
        self.jobs[index] = PlanJob(die.strip() or f"Arbeit {index + 1}", quantity, seconds)
        self._mark_changed()
        self._refresh_jobs()
        self.job_tree.selection_set(str(index))

    def remove_job(self) -> None:
        index = self._selection()
        if index is not None:
            self.jobs.pop(index)
            self._mark_changed()
            self._refresh_jobs()

    def _mark_changed(self) -> None:
        self.calculated_steps.clear()
        self.work_button.configure(state="disabled")
        if self.loaded_plan_name:
            self.saved_hint.configure(text=f"Geändert: {self.loaded_plan_name}")
        else:
            self.saved_hint.configure(text="Noch nicht gespeichert")

    def clear_jobs(self) -> None:
        self.jobs.clear()
        self._refresh_jobs()
        self.main_result.configure(text="Noch keine Arbeiten geplant")
        self.exact_result.configure(text="")
        self.result_lines.configure(text="")
        self.calculated_steps.clear()
        self.work_button.configure(state="disabled")
        self.loaded_plan_name = None
        self.saved_hint.configure(text="Noch nicht gespeichert")

    def _plan_data(self, name: str) -> dict:
        return {
            "name": name,
            "shift_number": self._selected_shift(),
            "start": self.start_entry.get().strip(),
            "jobs": [
                {"die": job.die, "quantity": job.quantity, "seconds_per_piece": job.seconds_per_piece}
                for job in self.jobs
            ],
        }

    def save_plan(self) -> None:
        if not self.jobs:
            messagebox.showinfo("Noch leer", "Bitte zuerst mindestens eine Arbeit hinzufügen.", parent=self)
            return
        name = simpledialog.askstring(
            "Schichtplan speichern", "Name des Plans:",
            initialvalue=self.loaded_plan_name or "", parent=self,
        )
        if name is None:
            return
        name = name.strip()
        try:
            self.plan_store.save(self._plan_data(name), replace_name=self.loaded_plan_name)
        except ValueError as error:
            messagebox.showerror("Plan nicht gespeichert", str(error), parent=self)
            return
        self.loaded_plan_name = name
        self.saved_hint.configure(text=f"Gespeichert: {name}")

    def _load_plan(self, plan: dict) -> None:
        number = int(plan["shift_number"])
        if number not in self.shift_options:
            raise ValueError("Die gespeicherte Schicht ist nicht mehr vorhanden.")
        self.shift_entry.set(self.shift_options[number])
        self._shift_selected()
        self._replace(self.start_entry, str(plan["start"]))
        self.jobs = [
            PlanJob(str(item["die"]), int(item["quantity"]), int(item["seconds_per_piece"]))
            for item in plan.get("jobs", [])
        ]
        self.loaded_plan_name = str(plan["name"])
        self.saved_hint.configure(text=f"Geladen: {self.loaded_plan_name}")
        self._refresh_jobs()
        self.calculate()

    def open_plan_manager(self) -> None:
        window = tk.Toplevel(self)
        window.title("Gespeicherte Schichtpläne")
        window.transient(self)
        window.grab_set()
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Gespeicherte Pläne", style="Title.TLabel").pack(anchor="w", pady=(0, 12))
        choice = ttk.Combobox(frame, state="readonly", width=42)
        choice.pack(fill="x", pady=(0, 12))

        def refresh(select: str | None = None) -> list[dict]:
            plans = self.plan_store.list()
            names = [str(item["name"]) for item in plans]
            choice.configure(values=names)
            if select in names:
                choice.set(select)
            elif names:
                choice.current(0)
            else:
                choice.set("")
            return plans

        def selected() -> dict | None:
            return next((item for item in self.plan_store.list() if item.get("name") == choice.get()), None)

        def load() -> None:
            plan = selected()
            if plan:
                try:
                    self._load_plan(plan)
                except (KeyError, TypeError, ValueError) as error:
                    messagebox.showerror("Plan nicht geladen", str(error), parent=window)
                    return
                window.destroy()

        def duplicate() -> None:
            plan = selected()
            if not plan:
                return
            new_name = simpledialog.askstring("Plan duplizieren", "Name der Kopie:", initialvalue=f"{plan['name']} Kopie", parent=window)
            if not new_name:
                return
            try:
                self.plan_store.duplicate(str(plan["name"]), new_name.strip())
            except ValueError as error:
                messagebox.showerror("Nicht dupliziert", str(error), parent=window)
                return
            refresh(new_name.strip())

        def delete() -> None:
            plan = selected()
            if not plan or not messagebox.askyesno("Plan löschen", f"„{plan['name']}“ wirklich löschen?", parent=window):
                return
            self.plan_store.delete(str(plan["name"]))
            if self.loaded_plan_name == plan["name"]:
                self.loaded_plan_name = None
                self.saved_hint.configure(text="Geladener Plan wurde gelöscht")
            refresh()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Laden", command=load).pack(side="left")
        ttk.Button(buttons, text="Duplizieren", command=duplicate).pack(side="left", padx=6)
        ttk.Button(buttons, text="Löschen", command=delete).pack(side="left")
        ttk.Button(buttons, text="Schließen", command=window.destroy).pack(side="right")
        refresh()

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
        self.calculated_steps = []
        for index, job in enumerate(self.jobs, 1):
            if cursor >= shift.end:
                lines.append(f"{index} · {job.die}: keine Schichtzeit mehr frei")
                continue
            result = calculate_shift_requirement(total_quantity=job.quantity, start=cursor, shift_end=shift.end, breaks=shift.breaks, seconds_per_piece=job.seconds_per_piece)
            exact = str(result.exact_pieces.quantize(Decimal("0.1"))).replace(".", ",")
            lines.append(f"{index} · {job.die}   {cursor:%H:%M} → {result.planned_end:%H:%M}\n    {result.complete_pieces} ganze Stück ({exact} rechnerisch) · danach {result.remaining_pieces} offen")
            scheduled += result.complete_pieces
            if result.complete_pieces:
                self.calculated_steps.append(
                    WorkStep(job.die, result.complete_pieces, result.complete_pieces * job.seconds_per_piece)
                )
            cursor = result.planned_end
            if result.remaining_pieces:
                for later_index, later in enumerate(self.jobs[index:], index + 1):
                    lines.append(f"{later_index} · {later.die}: keine Schichtzeit mehr frei")
                break
        self.main_result.configure(text=f"{len(self.jobs)} Arbeiten · {scheduled} ganze Stück geplant")
        self.exact_result.configure(text=f"Soll-Ablauf {start:%H:%M}–{cursor:%H:%M} · Schichtende {shift.end:%H:%M}")
        self.result_lines.configure(text="\n\n".join(lines))
        self.work_button.configure(state="normal" if self.calculated_steps else "disabled")

    def open_work_mode(self) -> None:
        if not self.calculated_steps:
            messagebox.showinfo("Zuerst berechnen", "Bitte den Schichtplan zuerst berechnen.", parent=self)
            return
        start = datetime.combine(self.plan_date, datetime.strptime(self.start_entry.get().strip(), "%H:%M").time())
        shift = self.service.shift_for_start(self._selected_shift(), start)
        WorkModeWindow(self, list(self.calculated_steps), shift.breaks)


def main() -> None:
    SimpleWerkMateApp().mainloop()
