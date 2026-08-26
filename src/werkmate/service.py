"""Anwendungslogik zwischen Bedienoberfläche, Rechenkern und Datenbank."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from .database import WerkMateDatabase
from .models import Shift
from .timecalc import (
    add_productive_duration,
    possible_complete_pieces,
    productive_duration_between,
    standard_shift,
    target_end,
)


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

    def quick_start(
        self,
        *,
        total_quantity: int,
        reported_start: datetime,
        shift_number: int,
        order_number: str = "",
        die_number: str = "",
        operation: str = "",
        seconds_per_piece: int | None = None,
        note: str = "",
    ) -> dict:
        """Legt aus Minimalangaben einen Auftrag an und startet die Schichtmenge."""
        if self.database.active_session() is not None:
            raise ValueError("Es läuft bereits ein persönlicher Arbeitseinsatz.")
        if total_quantity <= 0:
            raise ValueError("Die Gesamtmenge muss größer als null sein.")
        shift = shift_for_start(shift_number, reported_start)
        if reported_start >= shift.end:
            raise ValueError("Die Anmeldezeit liegt nicht vor dem Schichtende.")

        resolved_die = die_number.strip() or "MANUELL"
        resolved_operation = operation.strip().upper()
        resolved_seconds = seconds_per_piece
        source = "manuell"
        if resolved_seconds is None:
            if not die_number.strip():
                raise ValueError("Bitte Stückzeit oder eine Gesenknummer aus dem Katalog angeben.")
            standards = self.database.standards_for_die(die_number)
            if resolved_operation:
                standards = [
                    item for item in standards if item["operation_code"] == resolved_operation
                ]
            if not standards:
                raise ValueError("Für diese Auswahl wurde keine aktive Vorgabezeit gefunden.")
            if len(standards) > 1:
                raise ValueError("Dieses Gesenk besitzt mehrere Arbeitsgänge. Bitte einen auswählen.")
            standard = standards[0]
            resolved_operation = str(standard["operation_code"])
            resolved_seconds = int(standard["seconds_per_piece"])
            source = "katalog"
        if resolved_seconds <= 0:
            raise ValueError("Die Stückzeit muss größer als null sein.")
        resolved_operation = resolved_operation or "MANUELL"
        resolved_number = order_number.strip()
        if not resolved_number:
            base_number = f"SCHNELL-{reported_start:%Y%m%d-%H%M%S}"
            resolved_number = base_number
            suffix = 2
            while self.database.find_order(resolved_number) is not None:
                resolved_number = f"{base_number}-{suffix}"
                suffix += 1

        order_id = self.create_order(
            order_number=resolved_number,
            die_number=resolved_die,
            operation=resolved_operation,
            original_quantity=total_quantity,
            seconds_per_piece=resolved_seconds,
            note=note,
        )
        forecast = self.production_forecast(
            order_id=order_id,
            reported_start=reported_start,
            shift_number=shift_number,
        )
        planned_quantity = int(forecast["complete_pieces"])
        if planned_quantity == 0:
            planned_quantity = 1
        session_id = self.start_work(
            order_id=order_id,
            quantity=min(planned_quantity, total_quantity),
            reported_start=reported_start,
            shift_number=shift_number,
            note=note,
        )
        return {
            "order_id": order_id,
            "session_id": session_id,
            "order_number": resolved_number,
            "die_number": resolved_die,
            "operation": resolved_operation,
            "seconds_per_piece": resolved_seconds,
            "planned_quantity": min(planned_quantity, total_quantity),
            "source": source,
        }

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

    def production_forecast(
        self,
        *,
        order_id: int,
        reported_start: datetime,
        shift_number: int,
        custom_shift_end: datetime | None = None,
    ) -> dict:
        """Berechnet Sollstückzahl und vollständige Stücke bis Schichtende."""
        order = self.database.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        shift = with_custom_shift_end(
            shift_for_start(shift_number, reported_start), custom_shift_end
        )
        if reported_start >= shift.end:
            raise ValueError("Die Anmeldezeit liegt nicht vor dem Schichtende.")
        available = productive_duration_between(reported_start, shift.end, shift.breaks)
        available_seconds = int(available.total_seconds())
        seconds_per_piece = int(order["seconds_per_piece"])
        raw_equivalent = Decimal(available_seconds) / Decimal(seconds_per_piece)
        open_quantity = int(order["open_quantity"])
        target_equivalent = min(raw_equivalent, Decimal(open_quantity))
        complete_pieces = min(available_seconds // seconds_per_piece, open_quantity)
        used_seconds = complete_pieces * seconds_per_piece
        remainder_seconds = max(available_seconds - used_seconds, 0)
        has_more_pieces = open_quantity > complete_pieces
        next_piece_overtime = (
            max(seconds_per_piece - remainder_seconds, 0) if has_more_pieces else 0
        )
        return {
            "shift_name": shift.name,
            "shift_end": shift.end,
            "available_seconds": available_seconds,
            "target_equivalent": target_equivalent,
            "complete_pieces": complete_pieces,
            "remainder_seconds": remainder_seconds,
            "next_piece_overtime_seconds": next_piece_overtime,
            "next_piece_finish": (
                shift.end + timedelta(seconds=next_piece_overtime)
                if has_more_pieces else None
            ),
            "open_after_shift": max(open_quantity - complete_pieces, 0),
            "open_quantity": open_quantity,
        }

    def status(self, now: datetime | None = None) -> dict | None:
        session = self.database.active_session()
        if session is None:
            return None
        current = now or datetime.now().astimezone().replace(tzinfo=None)
        due = datetime.fromisoformat(session["target_end"])
        difference = due - current
        session["time_state"] = "verbleibend" if difference.total_seconds() >= 0 else "ueberzogen"
        session["time_seconds"] = abs(int(difference.total_seconds()))

        if session.get("session_kind") == "credit":
            order = self.database.get_order(int(session["order_id"]))
            session["credit_quantity"] = int(order["credit_quantity"]) if order else 0
            planned_seconds = int(session["planned_seconds"] or 0)
            session["credit_planned_seconds"] = planned_seconds
            session["credit_piece_equivalent"] = (
                Decimal(planned_seconds) / Decimal(int(session["seconds_per_piece"]))
            )
            return session

        if session["shift_end"]:
            shift_end = datetime.fromisoformat(session["shift_end"])
            # Die verrechenbare Pause steckt vor Soll-Ende. Für die Prognose
            # wird eine noch bevorstehende Standardpause anhand der Schicht rekonstruiert.
            shift_number = int(session["shift_name"].split()[-1])
            shift = shift_for_start(shift_number, datetime.fromisoformat(session["reported_started_at"]))
            reported_start = datetime.fromisoformat(session["reported_started_at"])
            pieces, remainder, overtime = possible_complete_pieces(
                reported_start,
                shift_end,
                int(session["seconds_per_piece"]),
                tuple(p for p in shift.breaks if p.end <= shift_end),
            )
            order = self.database.get_order(int(session["order_id"]))
            open_quantity = int(order["open_quantity"]) if order else int(session["quantity_to_process"])
            session["pieces_until_shift_end"] = min(pieces, open_quantity)
            session["unused_seconds"] = int(remainder.total_seconds())
            session["next_piece_overtime_seconds"] = (
                int(overtime.total_seconds()) if pieces < open_quantity else 0
            )
            session["next_piece_finish"] = (
                shift_end + overtime if pieces < open_quantity else None
            )
            available_seconds = int(
                productive_duration_between(
                    reported_start,
                    shift_end,
                    tuple(p for p in shift.breaks if p.end <= shift_end),
                ).total_seconds()
            )
            session["target_piece_equivalent"] = min(
                Decimal(available_seconds) / Decimal(int(session["seconds_per_piece"])),
                Decimal(open_quantity),
            )
            session["order_open_quantity"] = open_quantity
            session["order_open_seconds"] = open_quantity * int(session["seconds_per_piece"])
            session["beyond_shift_seconds"] = max(
                session["order_open_seconds"] - available_seconds, 0
            )
        return session

    def finish_work(
        self,
        session_id: int,
        *,
        completed_quantity: int,
        reported_quantity: int | None = None,
        reported_end: datetime,
        actual_confirmation: datetime | None = None,
        note: str = "",
    ) -> None:
        self.database.complete_session(
            session_id,
            completed_quantity=completed_quantity,
            reported_quantity=reported_quantity,
            actual_confirmed_at=(
                actual_confirmation or datetime.now().astimezone().replace(tzinfo=None)
            ),
            reported_ended_at=reported_end,
            note=note,
        )

    def finish_entire_order(
        self,
        session_id: int,
        *,
        reported_end: datetime,
        actual_confirmation: datetime | None = None,
        note: str = "",
        reported_quantity: int | None = None,
    ) -> int:
        session = self.database.get_session(session_id)
        if session is None:
            raise ValueError("Arbeitseinsatz nicht gefunden.")
        order = self.database.get_order(int(session["order_id"]))
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        quantity = int(order["open_quantity"])
        self.finish_work(
            session_id,
            completed_quantity=quantity,
            reported_quantity=reported_quantity,
            reported_end=reported_end,
            actual_confirmation=actual_confirmation,
            note=note,
        )
        return quantity

    def cancel_work(self, session_id: int, *, reason: str = "Fehlstart") -> None:
        self.database.cancel_session(session_id, reason=reason)

    def start_credit(
        self,
        *,
        order_id: int,
        reported_start: datetime,
        shift_number: int,
        quantity: int | None = None,
        productive_seconds: int | None = None,
        note: str = "",
    ) -> dict:
        order = self.database.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        credit_quantity = int(order["credit_quantity"])
        if credit_quantity <= 0:
            raise ValueError("Für diesen Auftrag ist kein Guthaben vorhanden.")
        seconds_per_piece = int(order["seconds_per_piece"])
        if quantity is not None:
            if quantity <= 0 or quantity > credit_quantity:
                raise ValueError("Die Guthabenstückzahl ist ungültig.")
            planned_seconds = quantity * seconds_per_piece
            suggested_quantity = quantity
            mode = "quantity"
        elif productive_seconds is not None:
            if productive_seconds <= 0:
                raise ValueError("Die Guthabenzeit muss größer als null sein.")
            equivalent = Decimal(productive_seconds) / Decimal(seconds_per_piece)
            suggested_quantity = int(
                equivalent.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            suggested_quantity = max(1, min(suggested_quantity, credit_quantity))
            planned_seconds = productive_seconds
            mode = "time"
        else:
            raise ValueError("Bitte Guthabenstückzahl oder Guthabenzeit angeben.")

        shift = shift_for_start(shift_number, reported_start)
        calculated_end = add_productive_duration(
            reported_start, timedelta(seconds=planned_seconds), shift.breaks
        )
        pause_seconds = int(
            (calculated_end - reported_start).total_seconds() - planned_seconds
        )
        session_id = self.database.start_session(
            order_id=order_id,
            shift_name=shift.name,
            shift_start=shift.start,
            shift_end=shift.end,
            quantity_to_process=suggested_quantity,
            seconds_per_piece=seconds_per_piece,
            actual_started_at=datetime.now().astimezone().replace(tzinfo=None),
            reported_started_at=reported_start,
            target_end=calculated_end,
            pause_seconds=pause_seconds,
            note=note,
            session_kind="credit",
            planned_seconds=planned_seconds,
        )
        return {
            "session_id": session_id,
            "mode": mode,
            "suggested_quantity": suggested_quantity,
            "piece_equivalent": Decimal(planned_seconds) / Decimal(seconds_per_piece),
            "planned_seconds": planned_seconds,
            "target_end": calculated_end,
            "credit_before": credit_quantity,
        }

    def finish_credit(
        self,
        session_id: int,
        *,
        reported_quantity: int,
        reported_end: datetime,
        actual_confirmation: datetime | None = None,
        note: str = "",
    ) -> None:
        session = self.database.get_session(session_id)
        if session is None or session["session_kind"] != "credit":
            raise ValueError("Guthabeneinsatz nicht gefunden.")
        self.database.complete_session(
            session_id,
            completed_quantity=0,
            reported_quantity=reported_quantity,
            actual_confirmed_at=(
                actual_confirmation or datetime.now().astimezone().replace(tzinfo=None)
            ),
            reported_ended_at=reported_end,
            note=note,
        )
