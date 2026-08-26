"""Anwendungslogik zwischen Bedienoberfläche, Rechenkern und Datenbank."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from .database import WerkMateDatabase
from .models import Shift
from .timecalc import possible_complete_pieces, standard_shift, target_end


def shift_for_start(number: int, reported_start: datetime) -> Shift:
    base_date = reported_start.date()
    if number == 3 and reported_start.time() < time(5, 45):
        base_date -= timedelta(days=1)
    return standard_shift(number, base_date)


def with_custom_shift_end(shift: Shift, new_end: datetime | None) -> Shift:
    if new_end is None:
        return shift
    valid_breaks = tuple(pause for pause in shift.breaks if pause.end <= new_end)
    return Shift(shift.name, shift.start, new_end, valid_breaks)


class WerkMateService:
    def __init__(self, database: WerkMateDatabase) -> None:
        self.database = database

    def create_order(
        self,
        *,
        order_number: str,
        die_number: str,
        operation: str,
        original_quantity: int,
        seconds_per_piece: int,
        note: str = "",
    ) -> int:
        if not order_number.strip() or not die_number.strip() or not operation.strip():
            raise ValueError("Auftragsnummer, Gesenknummer und Arbeitsgang sind Pflichtfelder.")
        if original_quantity <= 0 or seconds_per_piece <= 0:
            raise ValueError("Menge und Vorgabezeit müssen größer als null sein.")
        if self.database.find_order(order_number) is not None:
            raise ValueError("Diese Auftragsnummer ist bereits gespeichert.")
        return self.database.create_order(
            order_number=order_number,
            die_number=die_number,
            operation=operation,
            original_quantity=original_quantity,
            seconds_per_piece=seconds_per_piece,
            note=note,
        )

    def start_work(
        self,
        *,
        order_id: int,
        quantity: int,
        reported_start: datetime,
        actual_start: datetime | None = None,
        shift_number: int | None = None,
        custom_shift_end: datetime | None = None,
        note: str = "",
    ) -> int:
        order = self.database.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        if order["status"] == "abgegeben":
            raise ValueError("Dieser Restauftrag wurde aus der persönlichen Nachverfolgung abgegeben.")
        shift = (
            with_custom_shift_end(shift_for_start(shift_number, reported_start), custom_shift_end)
            if shift_number is not None
            else None
        )
        breaks = shift.breaks if shift else ()
        calculated_end = target_end(
            reported_start, quantity, int(order["seconds_per_piece"]), breaks
        )
        productive_seconds = quantity * int(order["seconds_per_piece"])
        pause_seconds = int(
            (calculated_end - reported_start).total_seconds() - productive_seconds
        )
        return self.database.start_session(
            order_id=order_id,
            shift_name=shift.name if shift else None,
            shift_start=shift.start if shift else None,
            shift_end=shift.end if shift else None,
            quantity_to_process=quantity,
            seconds_per_piece=int(order["seconds_per_piece"]),
            actual_started_at=actual_start or datetime.now().astimezone().replace(tzinfo=None),
            reported_started_at=reported_start,
            target_end=calculated_end,
            pause_seconds=pause_seconds,
            note=note,
        )

    def status(self, now: datetime | None = None) -> dict | None:
        session = self.database.active_session()
        if session is None:
            return None
        current = now or datetime.now().astimezone().replace(tzinfo=None)
        due = datetime.fromisoformat(session["target_end"])
        difference = due - current
        session["time_state"] = "verbleibend" if difference.total_seconds() >= 0 else "ueberzogen"
        session["time_seconds"] = abs(int(difference.total_seconds()))

        if session["shift_end"]:
            shift_end = datetime.fromisoformat(session["shift_end"])
            # Die verrechenbare Pause steckt vor Soll-Ende. Für die Prognose
            # wird eine noch bevorstehende Standardpause anhand der Schicht rekonstruiert.
            shift_number = int(session["shift_name"].split()[-1])
            shift = shift_for_start(shift_number, datetime.fromisoformat(session["reported_started_at"]))
            pieces, remainder, overtime = possible_complete_pieces(
                current,
                shift_end,
                int(session["seconds_per_piece"]),
                tuple(p for p in shift.breaks if p.end <= shift_end),
            )
            session["pieces_until_shift_end"] = pieces
            session["unused_seconds"] = int(remainder.total_seconds())
            session["next_piece_overtime_seconds"] = int(overtime.total_seconds())
        return session

    def finish_work(
        self,
        session_id: int,
        *,
        completed_quantity: int,
        reported_end: datetime,
        actual_confirmation: datetime | None = None,
        note: str = "",
    ) -> None:
        self.database.complete_session(
            session_id,
            completed_quantity=completed_quantity,
            actual_confirmed_at=(
                actual_confirmation or datetime.now().astimezone().replace(tzinfo=None)
            ),
            reported_ended_at=reported_end,
            note=note,
        )
