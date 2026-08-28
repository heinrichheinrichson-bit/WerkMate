"""Manueller, nicht automatisch weiterschaltender Arbeitsmodus."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
from tkinter import messagebox, simpledialog, ttk

from .models import BreakWindow
from .timecalc import add_productive_duration


def now_local() -> datetime:
    return datetime.now().astimezone().replace(tzinfo=None)


def clock(value: timedelta) -> str:
    seconds = max(int(value.total_seconds()), 0)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def next_clock_datetime(value: str, now: datetime) -> datetime:
    """Deutet eine reine Uhrzeit als nächsten zukünftigen Zeitpunkt, auch über Mitternacht."""
    entered = datetime.strptime(value.strip(), "%H:%M").time()
    candidate = datetime.combine(now.date(), entered)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


@dataclass(frozen=True)
class WorkStep:
    name: str
    pieces: int
    productive_seconds: int


class WorkModeWindow(tk.Toplevel):
    """Der nächste Schritt startet ausschließlich über den sichtbaren Startknopf."""

    def __init__(self, parent: tk.Misc, steps: list[WorkStep], breaks: tuple[BreakWindow, ...]) -> None:
        super().__init__(parent)
        self.title("WerkMate · Arbeitsmodus")
        self.geometry("720x570")
        self.minsize(620, 500)
        self.steps = steps
        self.breaks = breaks
        self.index = 0
        self.started_at: datetime | None = None
        self.target_end: datetime | None = None
        self.alarmed = False
        self.timer_id: str | None = None
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self._waiting_view()

    def _build(self) -> None:
        body = ttk.Frame(self, padding=26)
        body.pack(fill="both", expand=True)
        self.status = ttk.Label(body, text="BEREIT", style="Muted.TLabel")
        self.status.pack(anchor="w")
        self.title_label = ttk.Label(body, text="", style="Title.TLabel")
        self.title_label.pack(anchor="w", pady=(4, 4))
        self.detail = ttk.Label(body, text="", style="Muted.TLabel")
        self.detail.pack(anchor="w")
        self.timer = ttk.Label(body, text="00:00:00", style="Result.TLabel")
        self.timer.pack(anchor="center", pady=(34, 12))
        self.progress = ttk.Progressbar(body, maximum=100)
        self.progress.pack(fill="x")
        self.times = ttk.Label(body, text="", justify="center")
        self.times.pack(anchor="center", pady=(12, 20))
        next_card = ttk.LabelFrame(body, text="DANACH", style="Card.TLabelframe", padding=14)
        next_card.pack(fill="x")
        self.next_label = ttk.Label(next_card, text="")
        self.next_label.pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(22, 0))
        self.start_button = ttk.Button(actions, text="ARBEIT MANUELL STARTEN", style="Primary.TButton", command=self.start_current)
        self.start_button.pack(fill="x")
        self.running_actions = ttk.Frame(actions)
        ttk.Button(self.running_actions, text="ARBEIT FERTIG", style="Primary.TButton", command=self.finish_current).pack(side="left", fill="x", expand=True)
        ttk.Button(self.running_actions, text="ICH BRAUCHE LÄNGER", command=self.extend_current).pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _current(self) -> WorkStep:
        return self.steps[self.index]

    def _waiting_view(self) -> None:
        if self.index >= len(self.steps):
            self.status.configure(text="SCHICHTPLAN ABGEARBEITET")
            self.title_label.configure(text="Alle geplanten Arbeiten beendet")
            self.detail.configure(text="")
            self.next_label.configure(text="Keine weitere Arbeit geplant.")
            self.start_button.pack_forget()
            self.running_actions.pack_forget()
            return
        step = self._current()
        self.status.configure(text="WARTET AUF DEINEN START")
        self.title_label.configure(text=f"{self.index + 1} · {step.name}")
        self.detail.configure(text=f"{step.pieces} Stück · startet niemals automatisch")
        self.timer.configure(text="00:00:00", foreground="#175cd3")
        self.progress.configure(value=0)
        self.times.configure(text="Start und Soll-Ende werden beim manuellen Start gesetzt.")
        self._show_next()
        self.running_actions.pack_forget()
        self.start_button.configure(text="ARBEIT MANUELL STARTEN")
        self.start_button.pack(fill="x")

    def _show_next(self) -> None:
        following = self.index + 1
        if following < len(self.steps):
            step = self.steps[following]
            self.next_label.configure(text=f"{following + 1} · {step.name} · {step.pieces} Stück\nStart erst nach deinem Abschluss und deiner Bestätigung.")
        else:
            self.next_label.configure(text="Keine weitere Arbeit geplant.")

    def start_current(self) -> None:
        if self.index >= len(self.steps) or self.started_at is not None:
            return
        self.started_at = now_local()
        step = self._current()
        self.target_end = add_productive_duration(self.started_at, timedelta(seconds=step.productive_seconds), self.breaks)
        self.alarmed = False
        self.status.configure(text="LÄUFT")
        self.start_button.pack_forget()
        self.running_actions.pack(fill="x")
        self._tick()

    def _tick(self) -> None:
        if self.started_at is None or self.target_end is None:
            return
        now = now_local()
        remaining = self.target_end - now
        total = max((self.target_end - self.started_at).total_seconds(), 1)
        elapsed = max((now - self.started_at).total_seconds(), 0)
        self.progress.configure(value=min(elapsed / total * 100, 100))
        if remaining.total_seconds() >= 0:
            self.status.configure(text="LÄUFT")
            self.timer.configure(text=clock(remaining), foreground="#175cd3")
        else:
            self.status.configure(text="SOLLZEIT ABGELAUFEN · ÜBERZEIT")
            self.timer.configure(text=f"+ {clock(-remaining)}", foreground="#b42318")
            if not self.alarmed:
                self.alarmed = True
                self.bell()
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except (ImportError, RuntimeError):
                    pass
        self.times.configure(text=f"Gestartet: {self.started_at:%H:%M:%S}   ·   Soll-Ende: {self.target_end:%H:%M:%S}")
        self.timer_id = self.after(500, self._tick)

    def extend_current(self) -> None:
        if self.target_end is None:
            return
        value = simpledialog.askstring("Neue Soll-Endzeit", "Wann soll WerkMate erneut alarmieren? (HH:MM)", initialvalue=self.target_end.strftime("%H:%M"), parent=self)
        if not value:
            return
        try:
            candidate = next_clock_datetime(value, now_local())
        except ValueError:
            messagebox.showerror("Zeit nicht erkannt", "Bitte nur eine Uhrzeit wie 10:30 eingeben.", parent=self)
            return
        self.target_end = candidate
        self.alarmed = False

    def finish_current(self) -> None:
        if self.started_at is None:
            return
        self.started_at = None
        self.target_end = None
        self.alarmed = False
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.index += 1
        self._waiting_view()

    def _close(self) -> None:
        if self.started_at is not None and not messagebox.askyesno("Arbeitsmodus schließen", "Die aktuelle Arbeit läuft noch. Arbeitsmodus wirklich schließen?", parent=self):
            return
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.destroy()
