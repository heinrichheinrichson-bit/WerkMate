from datetime import datetime

import pytest

from werkmate.database import WerkMateDatabase
from werkmate.service import WerkMateService


def test_quick_start_with_only_quantity_and_piece_time(tmp_path) -> None:
    service = WerkMateService(WerkMateDatabase(tmp_path / "db.sqlite3"))
    result = service.quick_start(
        total_quantity=48,
        seconds_per_piece=1_200,
        reported_start=datetime(2026, 8, 26, 5, 45),
        shift_number=1,
    )
    assert result["source"] == "manuell"
    assert result["planned_quantity"] == 23
    assert result["die_number"] == "MANUELL"
    assert service.database.active_session()["target_end"] == "2026-08-26T13:43:00"


def test_quick_start_with_die_uses_single_catalog_standard(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    database.save_standard(
        die_number="8720", operation_code="FP", operation_name="Fertigputzen",
        seconds_per_piece=1_200,
    )
    service = WerkMateService(database)
    result = service.quick_start(
        total_quantity=24,
        die_number="8720",
        reported_start=datetime(2026, 8, 26, 13, 45),
        shift_number=2,
    )
    assert result["source"] == "katalog"
    assert result["operation"] == "FP"
    assert result["seconds_per_piece"] == 1_200


def test_quick_start_requires_operation_when_die_has_multiple(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    for code in ("FP1", "FP2"):
        database.save_standard(
            die_number="8720", operation_code=code, operation_name=code,
            seconds_per_piece=1_200,
        )
    service = WerkMateService(database)
    with pytest.raises(ValueError, match="mehrere Arbeitsgänge"):
        service.quick_start(
            total_quantity=24,
            die_number="8720",
            reported_start=datetime(2026, 8, 26, 13, 45),
            shift_number=2,
        )


def test_quick_start_can_select_one_of_multiple_operations(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    for code, seconds in (("FP1", 1_200), ("FP2", 900)):
        database.save_standard(
            die_number="8720", operation_code=code, operation_name=code,
            seconds_per_piece=seconds,
        )
    result = WerkMateService(database).quick_start(
        total_quantity=24,
        die_number="8720",
        operation="FP2",
        reported_start=datetime(2026, 8, 26, 13, 45),
        shift_number=2,
    )
    assert result["seconds_per_piece"] == 900


def test_generated_quick_order_numbers_do_not_collide(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    start = datetime(2026, 8, 26, 6)
    first = service.quick_start(
        total_quantity=1, seconds_per_piece=60, reported_start=start, shift_number=1
    )
    service.finish_entire_order(
        first["session_id"], reported_end=datetime(2026, 8, 26, 6, 1)
    )
    second = service.quick_start(
        total_quantity=1, seconds_per_piece=60, reported_start=start, shift_number=1
    )
    assert second["order_number"].endswith("-2")
