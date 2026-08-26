from datetime import datetime, timedelta

import pytest

from werkmate.database import WerkMateDatabase


@pytest.fixture
def database(tmp_path):
    return WerkMateDatabase(tmp_path / "werkmate.sqlite3")


def create_order(database: WerkMateDatabase) -> int:
    return database.create_order(
        order_number="FA-4711",
        die_number="8720",
        operation="FP1",
        original_quantity=24,
        seconds_per_piece=1_200,
        note="Wichtiger Auftrag",
    )


def test_order_is_stored_with_calculated_open_quantity(database) -> None:
    order_id = create_order(database)
    order = database.get_order(order_id)
    assert order["order_number"] == "FA-4711"
    assert order["open_quantity"] == 24
    assert order["note"] == "Wichtiger Auftrag"


def test_partial_report_keeps_order_open(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 13, 45)
    session_id = database.start_session(
        order_id=order_id,
        shift_name="Schicht 2",
        quantity_to_process=24,
        seconds_per_piece=1_200,
        actual_started_at=start,
        reported_started_at=start,
        target_end=start + timedelta(minutes=498),
        pause_seconds=1_080,
    )
    database.complete_session(
        session_id,
        completed_quantity=20,
        actual_confirmed_at=datetime(2026, 8, 26, 21, 50),
        reported_ended_at=datetime(2026, 8, 26, 21, 45),
        note="Rest wird morgen fortgesetzt",
    )
    order = database.get_order(order_id)
    assert order["completed_quantity"] == 20
    assert order["open_quantity"] == 4
    assert order["status"] == "teilweise_erledigt"
    assert database.get_session(session_id)["note"] == "Rest wird morgen fortgesetzt"


def test_multiple_sessions_complete_an_order(database) -> None:
    order_id = create_order(database)
    for day, quantity in [(26, 20), (27, 4)]:
        start = datetime(2026, 8, day, 6)
        session_id = database.start_session(
            order_id=order_id,
            shift_name="Schicht 1",
            quantity_to_process=quantity,
            seconds_per_piece=1_200,
            actual_started_at=start,
            reported_started_at=start,
            target_end=start + timedelta(minutes=quantity * 20),
            pause_seconds=0,
        )
        database.complete_session(
            session_id,
            completed_quantity=quantity,
            actual_confirmed_at=start + timedelta(minutes=quantity * 20),
            reported_ended_at=start + timedelta(minutes=quantity * 20),
        )
    order = database.get_order(order_id)
    assert order["open_quantity"] == 0
    assert order["status"] == "vollstaendig_erledigt"
    assert len(database.history()) == 2


def test_handed_off_means_not_personally_tracked(database) -> None:
    order_id = create_order(database)
    database.hand_off_order(order_id, reason="Kollege übernimmt")
    assert database.get_order(order_id)["status"] == "abgegeben"
    assert database.corrections("order", order_id)[0]["reason"] == "Kollege übernimmt"


def test_correction_preserves_old_and_new_value(database) -> None:
    order_id = create_order(database)
    database.update_field("order", order_id, "note", "Neue Notiz", reason="Ergänzt")
    correction = database.corrections("order", order_id)[0]
    assert correction["old_value"] == '"Wichtiger Auftrag"'
    assert correction["new_value"] == '"Neue Notiz"'


def test_only_one_active_session_can_be_found(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 13, 45)
    session_id = database.start_session(
        order_id=order_id,
        shift_name="Schicht 2",
        quantity_to_process=4,
        seconds_per_piece=1_200,
        actual_started_at=start,
        reported_started_at=start,
        target_end=start + timedelta(minutes=80),
        pause_seconds=0,
    )
    assert database.active_session()["id"] == session_id


def test_second_simultaneous_session_is_rejected(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 13, 45)
    arguments = dict(
        order_id=order_id,
        shift_name="Schicht 2",
        quantity_to_process=4,
        seconds_per_piece=1_200,
        actual_started_at=start,
        reported_started_at=start,
        target_end=start + timedelta(minutes=80),
        pause_seconds=0,
    )
    database.start_session(**arguments)
    with pytest.raises(ValueError, match="bereits"):
        database.start_session(**arguments)


def test_session_cannot_exceed_open_quantity(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 13, 45)
    with pytest.raises(ValueError, match="offene Auftragsmenge"):
        database.start_session(
            order_id=order_id,
            shift_name="Schicht 2",
            quantity_to_process=25,
            seconds_per_piece=1_200,
            actual_started_at=start,
            reported_started_at=start,
            target_end=start + timedelta(minutes=500),
            pause_seconds=0,
        )


def test_database_backup_contains_orders(database, tmp_path) -> None:
    create_order(database)
    backup_path = database.backup_to(tmp_path / "backup.sqlite3")
    backup = WerkMateDatabase(backup_path)
    assert backup.find_order("FA-4711")["die_number"] == "8720"


def test_order_edit_preserves_correction_history(database) -> None:
    order_id = create_order(database)
    database.update_order(
        order_id,
        die_number="8721",
        operation="FP2",
        original_quantity=25,
        seconds_per_piece=1_080,
        note="Vorgabe geändert",
    )
    order = database.get_order(order_id)
    assert order["die_number"] == "8721"
    assert order["seconds_per_piece"] == 1_080
    fields = {item["field_name"] for item in database.corrections("order", order_id)}
    assert fields == {"die_number", "operation", "original_quantity", "seconds_per_piece", "note"}


def test_order_quantity_cannot_be_reduced_below_reported_amount(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 6)
    session_id = database.start_session(
        order_id=order_id,
        shift_name="Schicht 1",
        quantity_to_process=20,
        seconds_per_piece=1_200,
        actual_started_at=start,
        reported_started_at=start,
        target_end=start + timedelta(hours=7),
        pause_seconds=0,
    )
    database.complete_session(
        session_id,
        completed_quantity=20,
        actual_confirmed_at=start + timedelta(hours=7),
        reported_ended_at=start + timedelta(hours=7),
    )
    with pytest.raises(ValueError, match="bereits gemeldete"):
        database.update_order(
            order_id,
            die_number="8720",
            operation="FP1",
            original_quantity=19,
            seconds_per_piece=1_200,
            note="",
        )


def test_handed_off_order_can_be_resumed(database) -> None:
    order_id = create_order(database)
    database.hand_off_order(order_id)
    database.resume_order(order_id)
    assert database.get_order(order_id)["status"] == "teilweise_erledigt"


def test_history_can_be_searched_and_filtered(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 6)
    database.start_session(
        order_id=order_id,
        shift_name="Schicht 1",
        quantity_to_process=4,
        seconds_per_piece=1_200,
        actual_started_at=start,
        reported_started_at=start,
        target_end=start + timedelta(minutes=80),
        pause_seconds=0,
        note="Sonderprüfung",
    )
    assert len(database.history(search="Sonderprüfung")) == 1
    assert len(database.history(search="FA-4711", status="laufend")) == 1
    assert database.history(status="abgeschlossen") == []


def test_accidental_session_start_can_be_cancelled_without_quantity(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 6)
    session_id = database.start_session(
        order_id=order_id,
        shift_name="Schicht 1",
        quantity_to_process=4,
        seconds_per_piece=1_200,
        actual_started_at=start,
        reported_started_at=start,
        target_end=start + timedelta(minutes=80),
        pause_seconds=0,
    )
    database.cancel_session(session_id, reason="Falsche Eingabe")
    session = database.get_session(session_id)
    assert session["status"] == "abgebrochen"
    assert session["completed_quantity"] == 0
    assert database.get_order(order_id)["open_quantity"] == 24
    assert database.active_session() is None
