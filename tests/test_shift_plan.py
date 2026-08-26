from datetime import datetime
from decimal import Decimal

from werkmate.database import WerkMateDatabase
from werkmate.service import WerkMateService


def test_fixed_first_order_then_fill_remaining_shift(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    first = service.create_order(
        order_number="FA-8720", die_number="8720", operation="FP",
        original_quantity=12, seconds_per_piece=20 * 60,
    )
    second = service.create_order(
        order_number="FA-4261", die_number="4261", operation="FP",
        original_quantity=40, seconds_per_piece=15 * 60,
    )
    plan = service.plan_sequence(
        items=[
            {"order_id": first, "mode": "work_fixed", "value": 12},
            {"order_id": second, "mode": "work_fill"},
        ],
        reported_start=datetime(2026, 8, 26, 5, 45),
        shift_number=1,
    )
    assert plan[0]["quantity"] == 12
    # 240 Minuten plus die Pause 08:45–09:03.
    assert plan[0]["planned_end"] == datetime(2026, 8, 26, 10, 3)
    # Von 10:03 bis 13:45 bleiben 222 produktive Minuten: 14,8 Stück.
    assert plan[1]["piece_equivalent"] == Decimal("14.8")
    assert plan[1]["quantity"] == 14
    assert plan[1]["planned_end"] == datetime(2026, 8, 26, 13, 33)
    assert plan[1]["overtime_seconds"] == 0


def test_credit_block_can_precede_new_work(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    credit_order = service.create_order(
        order_number="ALT", die_number="4261", operation="FP",
        original_quantity=20, seconds_per_piece=15 * 60,
    )
    work = service.start_work(
        order_id=credit_order, quantity=20,
        reported_start=datetime(2026, 8, 25, 6),
        actual_start=datetime(2026, 8, 25, 6),
    )
    service.finish_work(
        work, completed_quantity=20, reported_quantity=0,
        reported_end=datetime(2026, 8, 25, 11),
    )
    new_order = service.create_order(
        order_number="NEU", die_number="8720", operation="FP",
        original_quantity=40, seconds_per_piece=20 * 60,
    )
    plan = service.plan_sequence(
        items=[
            {"order_id": credit_order, "mode": "credit_time", "value": 120 * 60},
            {"order_id": new_order, "mode": "work_fill"},
        ],
        reported_start=datetime(2026, 8, 26, 5, 45),
        shift_number=1,
    )
    assert plan[0]["kind"] == "credit"
    assert plan[0]["planned_end"] == datetime(2026, 8, 26, 7, 45)
    assert plan[0]["quantity"] == 8
    assert plan[1]["planned_start"] == datetime(2026, 8, 26, 7, 45)
    # Noch 342 produktive Minuten nach Abzug der festen Pause.
    assert plan[1]["piece_equivalent"] == Decimal("17.1")
    assert plan[1]["quantity"] == 17
