"""Fachobjekte des unabhängigen WerkMate-Rechenkerns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class OrderStatus(StrEnum):
    OPEN = "offen"
    PARTIALLY_COMPLETED = "teilweise_erledigt"
    COMPLETED = "vollstaendig_erledigt"
    HANDED_OFF = "abgegeben"


class SessionStatus(StrEnum):
    RUNNING = "laufend"
    DUE = "sollzeit_erreicht"
    OVERDUE = "ueberzogen"
    INTERRUPTED = "unterbrochen"
    COMPLETED = "abgeschlossen"
    CORRECTED = "korrigiert"


@dataclass(frozen=True, slots=True)
class BreakWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("Das Pausenende muss nach dem Pausenbeginn liegen.")

    @property
    def duration(self) -> timedelta:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class Shift:
    name: str
    start: datetime
    end: datetime
    breaks: tuple[BreakWindow, ...] = ()

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("Das Schichtende muss nach dem Schichtbeginn liegen.")
        for pause in self.breaks:
            if pause.start < self.start or pause.end > self.end:
                raise ValueError("Eine Pause muss vollständig in der Schicht liegen.")


@dataclass(frozen=True, slots=True)
class Order:
    order_number: str
    die_number: str
    operation: str
    original_quantity: int
    seconds_per_piece: int
    note: str = ""
    completed_quantity: int = 0
    status: OrderStatus = OrderStatus.OPEN

    def __post_init__(self) -> None:
        if not self.order_number.strip():
            raise ValueError("Die Auftragsnummer darf nicht leer sein.")
        if not self.die_number.strip():
            raise ValueError("Die Gesenknummer darf nicht leer sein.")
        if not self.operation.strip():
            raise ValueError("Der Arbeitsgang darf nicht leer sein.")
        if self.original_quantity <= 0:
            raise ValueError("Die Auftragsmenge muss größer als null sein.")
        if self.seconds_per_piece <= 0:
            raise ValueError("Die Vorgabezeit muss größer als null sein.")
        if not 0 <= self.completed_quantity <= self.original_quantity:
            raise ValueError("Die fertiggemeldete Menge ist ungültig.")

    @property
    def open_quantity(self) -> int:
        return self.original_quantity - self.completed_quantity

    @property
    def total_target_duration(self) -> timedelta:
        return timedelta(seconds=self.original_quantity * self.seconds_per_piece)

    @property
    def open_target_duration(self) -> timedelta:
        return timedelta(seconds=self.open_quantity * self.seconds_per_piece)


@dataclass(slots=True)
class WorkSession:
    order_number: str
    quantity_to_process: int
    seconds_per_piece: int
    actual_started_at: datetime
    reported_started_at: datetime
    target_end: datetime
    shift_name: str | None = None
    actual_confirmed_at: datetime | None = None
    reported_ended_at: datetime | None = None
    completed_quantity: int | None = None
    note: str = ""
    status: SessionStatus = field(default=SessionStatus.RUNNING)

    @property
    def target_duration(self) -> timedelta:
        return timedelta(seconds=self.quantity_to_process * self.seconds_per_piece)

