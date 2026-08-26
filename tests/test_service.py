from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from werkmate.database import WerkMateDatabase
from werkmate.service import WerkMateService, shift_for_start


def test_night_shift_after_midnight_belongs_to_previous_date() -> None:
    shift = shift_for_start(3, datetime(2026, 8, 27, 1, 0))
    assert shift.start == datetime(2026, 8, 26, 21, 45)
    assert shift.end == datetime(2026, 8, 27, 5, 45)


def test_service_calculates_pause_and_status(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="FA-1",
        die_number="8720",
        operation="FP1",
        original_quantity=24,
        seconds_per_piece=1_200,
    )
    session_id = service.start_work(
        order_id=order_id,
        quantity=24,
        reported_start=datetime(2026, 8, 26, 13, 45),
        actual_start=datetime(2026, 8, 26, 13, 45),
        shift_number=2,
    )
    session = database.get_session(session_id)
    assert session["target_end"] == "2026-08-26T22:03:00"
    assert session["pause_seconds"] == 1_080

    status = service.status(datetime(2026, 8, 26, 18, 0))
    assert status["time_state"] == "verbleibend"
    assert status["time_seconds"] == 4 * 3_600 + 3 * 60
    assert status["pieces_until_shift_end"] == 23
    assert status["target_piece_equivalent"] == Decimal("23.1")
    assert status["unused_seconds"] == 2 * 60

    # Die Schichtprognose bleibt ab Anmeldung stabil und schrumpft nicht mit der Uhrzeit.
    later_status = service.status(datetime(2026, 8, 26, 20, 0))
    assert later_status["target_piece_equivalent"] == Decimal("23.1")
    assert later_status["next_piece_overtime_seconds"] == 18 * 60


def test_service_reports_overdue_and_finishes_partial_quantity(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="FA-2",
        die_number="8741",
        operation="KR",
        original_quantity=10,
        seconds_per_piece=600,
    )
    start = datetime(2026, 8, 26, 6)
    session_id = service.start_work(
        order_id=order_id,
        quantity=10,
        reported_start=start,
        actual_start=start,
    )
    status = service.status(datetime(2026, 8, 26, 7, 50))
    assert status["time_state"] == "ueberzogen"
    assert status["time_seconds"] == 10 * 60

    service.finish_work(
        session_id,
        completed_quantity=8,
        reported_end=datetime(2026, 8, 26, 7, 40),
        actual_confirmation=datetime(2026, 8, 26, 7, 50),
        note="Zwei Stück bleiben offen",
    )
    assert database.get_order(order_id)["open_quantity"] == 2
    assert database.active_session() is None


def test_duplicate_order_number_is_rejected_cleanly(tmp_path) -> None:
    service = WerkMateService(WerkMateDatabase(tmp_path / "db.sqlite3"))
    arguments = dict(
        order_number="FA-3", die_number="8720", operation="FP1",
        original_quantity=4, seconds_per_piece=600,
    )
    service.create_order(**arguments)
    with pytest.raises(ValueError, match="bereits"):
        service.create_order(**arguments)


def test_handed_off_order_cannot_be_started_again(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="FA-4", die_number="8720", operation="FP1",
        original_quantity=4, seconds_per_piece=600,
    )
    database.hand_off_order(order_id)
    with pytest.raises(ValueError, match="abgegeben"):
        service.start_work(
            order_id=order_id,
            quantity=4,
            reported_start=datetime(2026, 8, 26, 6),
        )


def test_early_shift_forecast_returns_decimal_target_and_complete_pieces(tmp_path) -> None:
    service = WerkMateService(WerkMateDatabase(tmp_path / "db.sqlite3"))
    order_id = service.create_order(
        order_number="FA-48", die_number="8720", operation="FP1",
        original_quantity=48, seconds_per_piece=1_200,
    )
    forecast = service.production_forecast(
        order_id=order_id,
        reported_start=datetime(2026, 8, 26, 5, 45),
        shift_number=1,
    )
    assert forecast["available_seconds"] == 462 * 60
    assert forecast["target_equivalent"] == Decimal("23.1")
    assert forecast["complete_pieces"] == 23
    assert forecast["remainder_seconds"] == 2 * 60
    assert forecast["next_piece_overtime_seconds"] == 18 * 60
    assert forecast["open_after_shift"] == 25
