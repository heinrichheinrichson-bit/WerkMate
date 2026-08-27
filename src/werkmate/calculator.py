"""Kleiner, unabhängiger Rechner für den WerkMate-Neustart."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR

from .models import BreakWindow
from .timecalc import add_productive_duration, productive_duration_between


@dataclass(frozen=True)
class CalculatorResult:
    seconds_per_piece: int
    total_seconds: int
    available_seconds: int
    exact_pieces: Decimal
    complete_pieces: int
    remaining_pieces: int
    planned_end: datetime


def calculate_shift_requirement(
    *,
    total_quantity: int,
    start: datetime,
    shift_end: datetime,
    breaks: tuple[BreakWindow, ...] | list[BreakWindow] = (),
    seconds_per_piece: int | None = None,
    total_seconds: int | None = None,
) -> CalculatorResult:
    """Berechnet den einfachen Schichtbedarf ohne Auftrag oder Rückmeldung."""
    if total_quantity <= 0:
        raise ValueError("Die Gesamtstückzahl muss größer als null sein.")
    if shift_end <= start:
        raise ValueError("Das Schichtende muss nach dem Arbeitsbeginn liegen.")
    if seconds_per_piece is None:
        if total_seconds is None or total_seconds <= 0:
            raise ValueError("Bitte Stückzeit oder Gesamtzeit eingeben.")
        seconds_per_piece = max(
            int((Decimal(total_seconds) / Decimal(total_quantity)).quantize(Decimal("1"))), 1
        )
    if seconds_per_piece <= 0:
        raise ValueError("Die Stückzeit muss größer als null sein.")

    calculated_total = total_quantity * seconds_per_piece
    available = max(
        int(productive_duration_between(start, shift_end, breaks).total_seconds()), 0
    )
    exact = min(
        Decimal(available) / Decimal(seconds_per_piece), Decimal(total_quantity)
    )
    complete = int(exact.quantize(Decimal("1"), rounding=ROUND_FLOOR))
    used_seconds = complete * seconds_per_piece
    planned_end = add_productive_duration(start, timedelta(seconds=used_seconds), breaks)
    return CalculatorResult(
        seconds_per_piece=seconds_per_piece,
        total_seconds=calculated_total,
        available_seconds=available,
        exact_pieces=exact,
        complete_pieces=complete,
        remaining_pieces=max(total_quantity - complete, 0),
        planned_end=planned_end,
    )
