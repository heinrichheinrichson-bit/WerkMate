from datetime import datetime, timedelta
from decimal import Decimal

from werkmate.database import WerkMateDatabase
from werkmate.service import WerkMateService


def prepare_credit(tmp_path, *, quantity=40, worked=40, reported=18, seconds=900):
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="FA-4261", die_number="4261", operation="FP",
        original_quantity=quantity, seconds_per_piece=seconds,
    )
    start = datetime(2026, 8, 26, 6)
    session_id = service.start_work(
        order_id=order_id, quantity=min(worked, quantity),
        reported_start=start, actual_start=start,
    )
    service.finish_work(
        session_id,
        completed_quantity=worked,
        reported_quantity=reported,
        reported_end=start + timedelta(seconds=worked * seconds),
        actual_confirmation=start + timedelta(seconds=worked * seconds),
    )
    return database, service, order_id


def test_worked_and_reported_quantities_create_credit(tmp_path) -> None:
    database, _service, order_id = prepare_credit(tmp_path)
    order = database.get_order(order_id)
    assert order["completed_quantity"] == 40
    assert order["reported_quantity"] == 18
    assert order["credit_quantity"] == 22
    assert order["open_quantity"] == 0
    assert order["status"] == "vollstaendig_erledigt"


def test_credit_can_be_consumed_by_piece_over_multiple_days(tmp_path) -> None:
    database, service, order_id = prepare_credit(tmp_path)
    result = service.start_credit(
        order_id=order_id,
        reported_start=datetime(2026, 8, 27, 5, 45),
        shift_number=1,
        quantity=10,
    )
    assert result["planned_seconds"] == 150 * 60
    service.finish_credit(
        result["session_id"],
        reported_quantity=10,
        reported_end=datetime(2026, 8, 27, 8, 15),
        actual_confirmation=datetime(2026, 8, 27, 8, 15),
    )
    assert database.get_order(order_id)["credit_quantity"] == 12

    result = service.start_credit(
        order_id=order_id,
        reported_start=datetime(2026, 8, 28, 5, 45),
        shift_number=1,
        quantity=5,
    )
    service.finish_credit(
        result["session_id"],
        reported_quantity=5,
        reported_end=datetime(2026, 8, 28, 7),
    )
    assert database.get_order(order_id)["credit_quantity"] == 7


def test_time_based_credit_keeps_exact_time_and_suggests_rounded_pieces(tmp_path) -> None:
    database, service, order_id = prepare_credit(
        tmp_path, quantity=20, worked=20, reported=0, seconds=17 * 60
    )
    result = service.start_credit(
        order_id=order_id,
        reported_start=datetime(2026, 8, 27, 5, 45),
        shift_number=1,
        productive_seconds=120 * 60,
    )
    assert result["piece_equivalent"].quantize(Decimal("0.01")) == Decimal("7.06")
    assert result["suggested_quantity"] == 7
    assert result["target_end"] == datetime(2026, 8, 27, 7, 45)

    # Der Benutzer entscheidet beim Abmelden selbst, hier bewusst 8 Stück.
    service.finish_credit(
        result["session_id"],
        reported_quantity=8,
        reported_end=datetime(2026, 8, 27, 7, 45),
    )
    order = database.get_order(order_id)
    assert order["credit_quantity"] == 12
    assert order["credit_quantity"] * order["seconds_per_piece"] == 204 * 60
