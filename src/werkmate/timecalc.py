"""Zeit-, Pausen-, Schicht- und Mengenberechnungen."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import BreakWindow, Shift


def minutes_to_seconds(value: str | int | float | Decimal) -> int:
    """Konvertiert auch deutsche Dezimaleingaben exakt in ganze Sekunden."""
    normalized = str(value).strip().replace(",", ".")
    try:
        minutes = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError("Ungültige Minutenangabe.") from error
    if minutes <= 0:
        raise ValueError("Die Minutenangabe muss größer als null sein.")
    return int((minutes * 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def seconds_to_minutes(seconds: int) -> Decimal:
    return (Decimal(seconds) / Decimal(60)).quantize(Decimal("0.01"))


def overlap_duration(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> timedelta:
    """Liefert die Überschneidung zweier halb-offener Zeitintervalle."""
    start = max(first_start, second_start)
    end = min(first_end, second_end)
    return max(end - start, timedelta(0))


def add_productive_duration(
    start: datetime,
    productive_duration: timedelta,
    breaks: tuple[BreakWindow, ...] | list[BreakWindow] = (),
) -> datetime:
    """Addiert Arbeitszeit und überspringt feste Pausenfenster."""
    if productive_duration < timedelta(0):
        raise ValueError("Die produktive Dauer darf nicht negativ sein.")

    cursor = start
    remaining = productive_duration
    for pause in sorted(breaks, key=lambda item: item.start):
        if pause.end <= cursor:
            continue

        if cursor < pause.start:
            available = pause.start - cursor
            if remaining <= available:
                return cursor + remaining
            remaining -= available
            cursor = pause.start

        if cursor < pause.end:
            cursor = pause.end

    return cursor + remaining


def productive_duration_between(
    start: datetime,
    end: datetime,
    breaks: tuple[BreakWindow, ...] | list[BreakWindow] = (),
) -> timedelta:
    """Berechnet die produktiv verfügbare Zeit in einem Kalenderintervall."""
    if end <= start:
        return timedelta(0)
    pause_time = sum(
        (overlap_duration(start, end, pause.start, pause.end) for pause in breaks),
        timedelta(0),
    )
    return max(end - start - pause_time, timedelta(0))


def target_end(
    reported_start: datetime,
    quantity: int,
    seconds_per_piece: int,
    breaks: tuple[BreakWindow, ...] | list[BreakWindow] = (),
) -> datetime:
    if quantity <= 0:
        raise ValueError("Die Menge muss größer als null sein.")
    if seconds_per_piece <= 0:
        raise ValueError("Die Stückzeit muss größer als null sein.")
    return add_productive_duration(
        reported_start,
        timedelta(seconds=quantity * seconds_per_piece),
        breaks,
    )


def remaining_or_overdue(target: datetime, now: datetime) -> tuple[str, timedelta]:
    """Gibt ('verbleibend'|'ueberzogen', stets positive Dauer) zurück."""
    difference = target - now
    if difference >= timedelta(0):
        return "verbleibend", difference
    return "ueberzogen", -difference


def possible_complete_pieces(
    start: datetime,
    shift_end: datetime,
    seconds_per_piece: int,
    breaks: tuple[BreakWindow, ...] | list[BreakWindow] = (),
) -> tuple[int, timedelta, timedelta]:
    """Liefert ganze Stücke, ungenutzte Zeit und Überzeit des nächsten Stücks."""
    if seconds_per_piece <= 0:
        raise ValueError("Die Stückzeit muss größer als null sein.")
    available = productive_duration_between(start, shift_end, breaks)
    available_seconds = int(available.total_seconds())
    pieces, remainder_seconds = divmod(available_seconds, seconds_per_piece)
    overtime = timedelta(seconds=(seconds_per_piece - remainder_seconds) % seconds_per_piece)
    if remainder_seconds == 0:
        overtime = timedelta(seconds=seconds_per_piece)
    return pieces, timedelta(seconds=remainder_seconds), overtime


DEFAULT_SHIFT_DEFINITIONS = {
    1: (time(5, 45), time(13, 45), time(8, 45), time(9, 3)),
    2: (time(13, 45), time(21, 45), time(17, 45), time(18, 3)),
    3: (time(21, 45), time(5, 45), time(1, 45), time(2, 3)),
}


def standard_shift(
    number: int,
    on_date: date,
    definition: tuple[time, time, time, time] | None = None,
) -> Shift:
    """Erzeugt eine konkrete Schicht; ohne Angabe gelten die WerkMate-Standardzeiten."""
    try:
        start_time, end_time, pause_start_time, pause_end_time = (
            definition or DEFAULT_SHIFT_DEFINITIONS[number]
        )
    except KeyError as error:
        raise ValueError("Die Schichtnummer muss 1, 2 oder 3 sein.") from error

    overnight = end_time <= start_time
    start = datetime.combine(on_date, start_time)
    next_date = on_date + timedelta(days=1) if overnight else on_date
    end = datetime.combine(next_date, end_time)
    pause_date = next_date if overnight and pause_start_time < start_time else on_date
    pause_end_date = (
        pause_date + timedelta(days=1) if pause_end_time <= pause_start_time else pause_date
    )
    pause = BreakWindow(
        datetime.combine(pause_date, pause_start_time),
        datetime.combine(pause_end_date, pause_end_time),
    )
    if pause.start < start or pause.end > end:
        raise ValueError("Die Pause muss vollständig innerhalb der Schicht liegen.")
    return Shift(f"Schicht {number}", start, end, (pause,))
