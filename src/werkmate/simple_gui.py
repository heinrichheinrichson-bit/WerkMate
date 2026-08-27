"""Bewusst kleine WerkMate-Oberfläche: ein Rechner, eine Aufgabe."""

from __future__ import annotations

import tkinter as tk
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


class SimpleWerkMateApp(tk.Tk):
    VERSION = "Simple 0.1"

    def __init__(self, database_path=None) -> None:
        super().__init__()
        self.title(f"WerkMate · {self.VERSION}")
        self.geometry("760x720")
        self.minsize(680, 650)
        self.database = WerkMateDatabase(database_path or default_database_path())
        self.service = WerkMateService(self.database)
        self.plan_date = local_now().date()
        self._configure_style()
        self._build_ui()
        self._load_catalog_values()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.configure(background="#f4f6f8")
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8", font=("Segoe UI", 11))
        style.configure("Muted.TLabel", foreground="#667085")
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground="#101828")
        style.configure("Result.TLabel", font=("Segoe UI", 26, "bold"), foreground="#175cd3")
        style.configure("Card.TLabelframe", background="#ffffff", bordercolor="#d0d5dd")
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure(
            "Primary.TButton", font=("Segoe UI", 13, "bold"), padding=(18, 14),
            background="#2f6fed", foreground="#ffffff",
        )
        style.map("Primary.TButton", background=[("active", "#175cd3")])
        style.configure("TEntry", padding=8)
        style.configure("TCombobox", padding=8)

    def _build_ui(self) -> None:
        content = ttk.Frame(self, padding=28)
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="WerkMate Rechner", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            content, text="Wie viele Stück brauche ich bis zum Schichtende?",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 22))

        inputs = ttk.LabelFrame(content, text="ANGABEN", style="Card.TLabelframe", padding=16)
        inputs.pack(fill="x")
        inputs.columnconfigure(0, weight=1)
        inputs.columnconfigure(1, weight=1)

        ttk.Label(inputs, text="Gesenknummer (optional)").grid(row=0, column=0, sticky="w")
        self.die_entry = ttk.Combobox(inputs)
        self.die_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 14))
        self.die_entry.bind("<<ComboboxSelected>>", self._catalog_selected)
        ttk.Label(inputs, text="Gesamtstück").grid(row=0, column=1, sticky="w")
        self.quantity_entry = ttk.Entry(inputs)
        self.quantity_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 14))

        ttk.Label(inputs, text="Stückzeit in Minuten").grid(row=2, column=0, sticky="w")
        self.piece_time_entry = ttk.Entry(inputs)
        self.piece_time_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(4, 6))
        ttk.Label(inputs, text="oder Gesamtzeit in Minuten").grid(row=2, column=1, sticky="w")
        self.total_time_entry = ttk.Entry(inputs)
        self.total_time_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(4, 6))

        shift = ttk.LabelFrame(content, text="SCHICHT", style="Card.TLabelframe", padding=16)
        shift.pack(fill="x", pady=14)
        shift.columnconfigure(0, weight=2)
        shift.columnconfigure(1, weight=1)
        ttk.Label(shift, text="Welche Schicht?").grid(row=0, column=0, sticky="w")
        self.shift_options = self._shift_labels()
        self.shift_entry = ttk.Combobox(
            shift, values=tuple(self.shift_options.values()), state="readonly"
        )
        current_number = self._current_shift_number(local_now())
        self.shift_entry.set(self.shift_options[current_number])
        self.shift_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        self.shift_entry.bind("<<ComboboxSelected>>", self._shift_selected)
        ttk.Label(shift, text="Arbeitsbeginn").grid(row=0, column=1, sticky="w")
        self.start_entry = ttk.Entry(shift)
        self.start_entry.insert(0, local_now().strftime("%H:%M"))
        self.start_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.date_hint = ttk.Label(shift, text="", style="Muted.TLabel")
        self.date_hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._update_date_hint()

        ttk.Button(
            content, text="BERECHNEN", style="Primary.TButton", command=self.calculate
        ).pack(fill="x", pady=(4, 14))

        result = ttk.LabelFrame(content, text="ERGEBNIS", style="Card.TLabelframe", padding=18)
        result.pack(fill="both", expand=True)
        self.main_result = ttk.Label(result, text="– Stück", style="Result.TLabel")
        self.main_result.pack(anchor="w")
        self.exact_result = ttk.Label(
            result, text="Hier erscheint die benötigte Stückzahl.", style="Muted.TLabel"
        )
        self.exact_result.pack(anchor="w", pady=(3, 16))
        self.result_lines = ttk.Label(result, text="", justify="left")
        self.result_lines.pack(anchor="w")

    def _shift_labels(self) -> dict[int, str]:
        names = {1: "Frühschicht", 2: "Spätschicht", 3: "Nachtschicht"}
        return {
            int(item["shift_number"]): (
                f"{names[int(item['shift_number'])]} · {item['start_time']}–{item['end_time']}"
            )
            for item in self.database.shift_settings()
        }

    def _current_shift_number(self, now: datetime) -> int:
        current = now.time()
        for item in self.database.shift_settings():
            start = datetime.strptime(item["start_time"], "%H:%M").time()
            end = datetime.strptime(item["end_time"], "%H:%M").time()
            inside = start <= current < end if start < end else current >= start or current < end
            if inside:
                return int(item["shift_number"])
        return 1

    def _selected_shift_number(self) -> int:
        for number, label in self.shift_options.items():
            if self.shift_entry.get() == label:
                return number
        raise ValueError("Bitte eine Schicht auswählen.")

    def _shift_selected(self, _event=None) -> None:
        number = self._selected_shift_number()
        setting = next(
            item for item in self.database.shift_settings()
            if int(item["shift_number"]) == number
        )
        now = local_now()
        clock = datetime.strptime(setting["start_time"], "%H:%M").time()
        candidate = datetime.combine(now.date(), clock)
        if candidate < now:
            candidate += timedelta(days=1)
        self.plan_date = candidate.date()
        self._replace(self.start_entry, candidate.strftime("%H:%M"))
        self._update_date_hint()

    def _update_date_hint(self) -> None:
        today = local_now().date()
        name = "heute" if self.plan_date == today else "morgen" if self.plan_date == today + timedelta(days=1) else self.plan_date.strftime("%d.%m.%Y")
        self.date_hint.configure(text=f"Geplant für {name}. Pausen werden automatisch berücksichtigt.")

    def _load_catalog_values(self) -> None:
        values = sorted({item["die_number"] for item in self.database.list_catalog()})
        self.die_entry.configure(values=values)

    def _catalog_selected(self, _event=None) -> None:
        matches = self.database.standards_for_die(self.die_entry.get().strip())
        times = {int(item["seconds_per_piece"]) for item in matches}
        if len(times) == 1:
            self._replace(self.piece_time_entry, str(seconds_to_minutes(times.pop())).replace(".", ","))

    @staticmethod
    def _replace(entry: ttk.Entry, value: str) -> None:
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def _resolve_piece_seconds(self) -> int | None:
        if self.piece_time_entry.get().strip():
            return minutes_to_seconds(self.piece_time_entry.get())
        die = self.die_entry.get().strip()
        if not die:
            return None
        matches = self.database.standards_for_die(die)
        times = {int(item["seconds_per_piece"]) for item in matches}
        if len(times) == 1:
            seconds = times.pop()
            self._replace(self.piece_time_entry, str(seconds_to_minutes(seconds)).replace(".", ","))
            return seconds
        if len(times) > 1:
            raise ValueError("Für dieses Gesenk gibt es mehrere Stückzeiten. Bitte Stückzeit eingeben.")
        return None

    def calculate(self) -> None:
        try:
            quantity = int(self.quantity_entry.get())
            start_clock = datetime.strptime(self.start_entry.get().strip(), "%H:%M").time()
            start = datetime.combine(self.plan_date, start_clock)
            shift = self.service.shift_for_start(self._selected_shift_number(), start)
            if start < shift.start or start >= shift.end:
                raise ValueError(
                    f"Der Arbeitsbeginn {start:%H:%M} liegt nicht in der gewählten Schicht "
                    f"({shift.start:%H:%M}–{shift.end:%H:%M})."
                )
            result = calculate_shift_requirement(
                total_quantity=quantity,
                start=start,
                shift_end=shift.end,
                breaks=shift.breaks,
                seconds_per_piece=self._resolve_piece_seconds(),
                total_seconds=(
                    minutes_to_seconds(self.total_time_entry.get())
                    if self.total_time_entry.get().strip() else None
                ),
            )
        except (ValueError, TypeError) as error:
            messagebox.showerror("Eingabe prüfen", str(error), parent=self)
            return

        self._replace(
            self.piece_time_entry,
            str(seconds_to_minutes(result.seconds_per_piece)).replace(".", ","),
        )
        self._replace(
            self.total_time_entry,
            str(seconds_to_minutes(result.total_seconds)).replace(".", ","),
        )
        exact = result.exact_pieces.quantize(Decimal("0.1"))
        self.main_result.configure(text=f"{result.complete_pieces} ganze Stück")
        self.exact_result.configure(
            text=f"Rechnerisch {str(exact).replace('.', ',')} Stück bis Schichtende"
        )
        self.result_lines.configure(
            text=(
                f"Arbeitsbeginn:  {start:%H:%M}\n"
                f"Schichtende:    {shift.end:%H:%M}\n"
                f"Ende der ganzen Stück:  {result.planned_end:%H:%M}\n"
                f"Danach offen:   {result.remaining_pieces} Stück\n"
                f"Produktive Restzeit:  {seconds_to_minutes(result.available_seconds)} Minuten\n"
                f"Gesamtzeit des Auftrags:  {seconds_to_minutes(result.total_seconds)} Minuten"
            )
        )


def main() -> None:
    SimpleWerkMateApp().mainloop()
