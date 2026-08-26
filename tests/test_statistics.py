from datetime import date, datetime

from werkmate.database import WerkMateDatabase
from werkmate.service import WerkMateService


def test_statistics_aggregate_time_pieces_and_credit(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    service = WerkMateService(database)
    order_id = service.create_order(
        order_number="STAT", die_number="8720", operation="FP",
        original_quantity=20, seconds_per_piece=600,
    )
    session_id = service.start_work(
        order_id=order_id, quantity=6,
        reported_start=datetime(2026, 8, 26, 6),
        actual_start=datetime(2026, 8, 26, 6),
    )
    service.finish_work(
        session_id, completed_quantity=7, reported_quantity=5,
        reported_end=datetime(2026, 8, 26, 7, 5),
        actual_confirmation=datetime(2026, 8, 26, 7, 5),
    )

    result = service.statistics(date(2026, 8, 26), date(2026, 8, 26))
    total = result["total"]
    assert total["sessions"] == 1
    assert total["completed"] == 7
    assert total["reported"] == 5
    assert total["credit_change"] == 2
    assert total["planned_quantity"] == 6
    assert total["measured_quantity"] == 7
    assert total["planned_seconds"] == 3_600
    assert total["actual_seconds"] == 3_900
