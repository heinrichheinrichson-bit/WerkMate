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


def test_capped_order_plans_only_required_pieces_for_current_shift(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="FA-48", die_number="8720", operation="FP",
        original_quantity=48, seconds_per_piece=20 * 60,
    )
    plan = service.plan_sequence(
        items=[{"order_id": order_id, "mode": "work_capped", "value": 48}],
        reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1,
    )
    assert plan[0]["piece_equivalent"] == Decimal("23.1")
    assert plan[0]["quantity"] == 23
    assert plan[0]["remaining_after_plan"] == 25
    assert plan[0]["planned_end"] == datetime(2026, 8, 26, 13, 43)
    assert plan[0]["overtime_seconds"] == 0


def test_capped_order_uses_explicit_overtime_shift_end(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="FA-LANG", die_number="8720", operation="FP",
        original_quantity=48, seconds_per_piece=20 * 60,
    )
    plan = service.plan_sequence(
        items=[{"order_id": order_id, "mode": "work_capped", "value": 48}],
        reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1,
        custom_shift_end=datetime(2026, 8, 26, 15, 45),
    )
    assert plan[0]["piece_equivalent"] == Decimal("29.1")
    assert plan[0]["quantity"] == 29
    assert plan[0]["remaining_after_plan"] == 19
    assert plan[0]["overtime_seconds"] == 0


def test_custom_shift_end_is_persisted_with_plan(tmp_path) -> None:
    path = tmp_path / "db.sqlite3"
    database = WerkMateDatabase(path)
    order_id = database.create_order(
        order_number="FA-PLANENDE", die_number="8720", operation="FP",
        original_quantity=48, seconds_per_piece=20 * 60,
    )
    custom_end = datetime(2026, 8, 26, 15, 45)
    database.save_shift_plan(
        reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1,
        custom_shift_end=custom_end,
        items=[{"order_id": order_id, "mode": "work_capped", "value": 48}],
    )
    reopened = WerkMateDatabase(path).active_shift_plan()
    assert reopened is not None
    assert reopened["custom_shift_end"] == custom_end.isoformat()


def test_capped_small_order_leaves_capacity_for_following_order(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    first = service.create_order(
        order_number="KLEIN", die_number="8720", operation="FP",
        original_quantity=12, seconds_per_piece=20 * 60,
    )
    second = service.create_order(
        order_number="WEITER", die_number="4261", operation="FP",
        original_quantity=40, seconds_per_piece=15 * 60,
    )
    plan = service.plan_sequence(
        items=[
            {"order_id": first, "mode": "work_capped", "value": 12},
            {"order_id": second, "mode": "work_capped", "value": 40},
        ],
        reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1,
    )
    assert plan[0]["quantity"] == 12
    assert plan[1]["piece_equivalent"] == Decimal("14.8")
    assert plan[1]["quantity"] == 14
    assert plan[1]["remaining_after_plan"] == 26


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


def test_saved_plan_survives_restart_and_advances_from_actual_report_time(tmp_path) -> None:
    path = tmp_path / "db.sqlite3"
    database = WerkMateDatabase(path)
    service = WerkMateService(database)
    first = service.create_order(
        order_number="ERST", die_number="8720", operation="FP",
        original_quantity=12, seconds_per_piece=20 * 60,
    )
    second = service.create_order(
        order_number="DANACH", die_number="4261", operation="FP",
        original_quantity=40, seconds_per_piece=15 * 60,
    )
    database.save_shift_plan(
        reported_start=datetime(2026, 8, 26, 5, 45),
        shift_number=1,
        items=[
            {"order_id": first, "mode": "work_fixed", "value": 12},
            {"order_id": second, "mode": "work_fill", "value": None},
        ],
    )

    reopened = WerkMateDatabase(path)
    saved = reopened.active_shift_plan()
    assert saved is not None
    assert [item["order_number"] for item in saved["items"]] == ["ERST", "DANACH"]

    session_id = WerkMateService(reopened).start_work(
        order_id=first, quantity=12,
        reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1,
    )
    reopened.link_shift_plan_session(saved["items"][0]["id"], session_id)
    WerkMateService(reopened).finish_work(
        session_id, completed_quantity=12, reported_quantity=12,
        reported_end=datetime(2026, 8, 26, 10, 18),
    )

    advanced = reopened.active_shift_plan()
    assert advanced is not None
    assert advanced["reported_start"] == datetime(2026, 8, 26, 10, 18).isoformat()
    assert advanced["items"][0]["status"] == "erledigt"
    remaining = WerkMateService(reopened).plan_sequence(
        items=[advanced["items"][1]],
        reported_start=datetime.fromisoformat(advanced["reported_start"]),
        shift_number=advanced["shift_number"],
    )
    assert remaining[0]["planned_start"] == datetime(2026, 8, 26, 10, 18)
    assert remaining[0]["quantity"] == 13


def test_manual_start_override_creates_a_gap_and_is_persisted(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    first = service.create_order(
        order_number="A", die_number="1", operation="FP",
        original_quantity=1, seconds_per_piece=30 * 60,
    )
    second = database.create_order(
        order_number="PLAN-MANUELL", die_number="X", operation="ZP",
        original_quantity=2, seconds_per_piece=15 * 60, is_temporary=True,
    )
    items = [
        {"order_id": first, "mode": "work_fixed", "value": 1},
        {"order_id": second, "mode": "work_fixed", "value": 2,
         "start_override": datetime(2026, 8, 26, 7)},
    ]
    result = service.plan_sequence(
        items=items, reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1,
    )
    assert result[0]["planned_end"] == datetime(2026, 8, 26, 6, 15)
    assert result[1]["planned_start"] == datetime(2026, 8, 26, 7)
    assert second not in {item["id"] for item in database.list_orders()}

    database.save_shift_plan(
        reported_start=datetime(2026, 8, 26, 5, 45), shift_number=1, items=items,
    )
    saved = database.active_shift_plan()
    assert saved["items"][1]["start_override"] == "2026-08-26T07:00:00"


def test_pending_plan_can_be_reordered_while_first_item_is_running(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    ids = [service.create_order(
        order_number=number, die_number=number, operation="FP",
        original_quantity=2, seconds_per_piece=600,
    ) for number in ("A", "B", "C")]
    original = [{"order_id": item, "mode": "work_fixed", "value": 1} for item in ids]
    database.save_shift_plan(
        reported_start=datetime(2026, 8, 26, 6), shift_number=1, items=original,
    )
    saved = database.active_shift_plan()
    session_id = service.start_work(
        order_id=ids[0], quantity=1, reported_start=datetime(2026, 8, 26, 6), shift_number=1,
    )
    database.link_shift_plan_session(saved["items"][0]["id"], session_id)

    database.save_shift_plan(
        reported_start=datetime(2026, 8, 26, 6, 10), shift_number=1,
        items=[original[2], original[1]],
    )
    updated = database.active_shift_plan()
    assert [item["order_number"] for item in updated["items"]] == ["A", "C", "B"]
    assert updated["items"][0]["status"] == "laufend"
