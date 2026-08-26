import sqlite3
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
    with pytest.raises(ValueError, match="verfügbare Auftragsmenge"):
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


def test_completed_session_correction_recalculates_order_and_keeps_audit(database) -> None:
    order_id = database.create_order(
        order_number="KORR", die_number="8720", operation="FP",
        original_quantity=10, seconds_per_piece=600,
    )
    session_id = database.start_session(
        order_id=order_id, shift_name="Schicht 1", quantity_to_process=5,
        seconds_per_piece=600, actual_started_at=datetime(2026, 8, 26, 6),
        reported_started_at=datetime(2026, 8, 26, 6),
        target_end=datetime(2026, 8, 26, 6, 50), pause_seconds=0,
    )
    database.complete_session(
        session_id, completed_quantity=5, reported_quantity=5,
        actual_confirmed_at=datetime(2026, 8, 26, 7),
        reported_ended_at=datetime(2026, 8, 26, 7),
    )
    database.correct_session(
        session_id,
        reported_started_at=datetime(2026, 8, 26, 6, 10),
        reported_ended_at=datetime(2026, 8, 26, 7, 5),
        completed_quantity=7, reported_quantity=5,
        note="Zählfehler berichtigt", reason="Zettel geprüft",
    )
    order = database.get_order(order_id)
    session = database.get_session(session_id)
    assert order["completed_quantity"] == 7
    assert order["credit_quantity"] == 2
    assert session["target_end"] == datetime(2026, 8, 26, 7).isoformat()
    fields = {item["field_name"] for item in database.corrections("session", session_id)}
    assert {"reported_started_at", "target_end", "reported_ended_at", "completed_quantity", "note"} <= fields


def test_csv_export_and_validated_restore(database, tmp_path) -> None:
    create_order(database)
    export_dir = tmp_path / "export"
    orders_path, history_path = database.export_csv(export_dir)
    assert orders_path.read_text(encoding="utf-8-sig").startswith("Auftragsnummer;")
    assert "FA-4711" in orders_path.read_text(encoding="utf-8-sig")
    assert history_path.read_text(encoding="utf-8-sig").startswith("ID;")

    backup = tmp_path / "backup.sqlite3"
    database.backup_to(backup)
    database.create_order(
        order_number="SPAETER", die_number="X", operation="FP",
        original_quantity=1, seconds_per_piece=60,
    )
    assert database.find_order("SPAETER") is not None
    database.restore_from(backup)
    assert database.find_order("FA-4711") is not None
    assert database.find_order("SPAETER") is None


def test_restore_rejects_unrelated_sqlite_file(database, tmp_path) -> None:
    unrelated = WerkMateDatabase(tmp_path / "temporary.sqlite3")
    unrelated.path.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        database.restore_from(unrelated.path)


def test_duplicate_archive_and_order_trash(database) -> None:
    original_id = create_order(database)
    copy_id = database.duplicate_order(original_id)
    copy = database.get_order(copy_id)
    assert copy["order_number"] == "FA-4711-KOPIE"
    assert copy["die_number"] == "8720"
    assert copy["original_quantity"] == 24

    database.archive_order(copy_id)
    assert copy_id not in {item["id"] for item in database.list_orders()}
    assert copy_id in {item["id"] for item in database.list_orders(include_archived=True)}
    database.restore_archived_order(copy_id)
    assert database.get_order(copy_id)["status"] == "offen"
    database.archive_order(copy_id)
    database.permanently_delete_archived_order(copy_id)
    assert database.get_order(copy_id) is None


def test_voided_report_is_hidden_reversible_and_excluded_from_totals(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 6)
    session_id = database.start_session(
        order_id=order_id, shift_name="Schicht 1", quantity_to_process=4,
        seconds_per_piece=1200, actual_started_at=start, reported_started_at=start,
        target_end=start + timedelta(minutes=80), pause_seconds=0,
    )
    database.complete_session(
        session_id, completed_quantity=4, reported_quantity=4,
        actual_confirmed_at=start + timedelta(minutes=80),
        reported_ended_at=start + timedelta(minutes=80),
    )
    database.void_session(session_id, reason="Testeintrag")
    assert database.get_order(order_id)["completed_quantity"] == 0
    assert database.history() == []
    assert database.history(status="storniert")[0]["id"] == session_id
    database.restore_voided_session(session_id)
    assert database.get_order(order_id)["completed_quantity"] == 4
    assert database.history()[0]["status"] == "abgeschlossen"


def test_running_and_cancelled_history_entries_can_be_moved_to_trash(database) -> None:
    order_id = create_order(database)
    start = datetime(2026, 8, 26, 6)
    running_id = database.start_session(
        order_id=order_id, shift_name="Schicht 1", quantity_to_process=2,
        seconds_per_piece=1200, actual_started_at=start, reported_started_at=start,
        target_end=start + timedelta(minutes=40), pause_seconds=0,
    )
    database.void_session(running_id, reason="Teststart löschen")
    assert database.active_session() is None
    assert database.get_session(running_id)["status"] == "storniert"
    database.restore_voided_session(running_id)
    assert database.get_session(running_id)["status"] == "abgebrochen"

    cancelled_id = database.start_session(
        order_id=order_id, shift_name="Schicht 1", quantity_to_process=2,
        seconds_per_piece=1200, actual_started_at=start, reported_started_at=start,
        target_end=start + timedelta(minutes=40), pause_seconds=0,
    )
    database.cancel_session(cancelled_id)
    database.void_session(cancelled_id, reason="Abbruch aus Historie entfernen")
    assert database.get_session(cancelled_id)["status"] == "storniert"


def test_quick_order_number_can_be_completed_later(database) -> None:
    order_id = create_order(database)
    database.update_order(
        order_id, order_number="ECHTE-4711", die_number="9999", operation="ZP",
        original_quantity=24, seconds_per_piece=900, note="nachgetragen",
    )
    order = database.get_order(order_id)
    assert order["order_number"] == "ECHTE-4711"
    assert order["die_number"] == "9999"


def test_active_session_can_be_extended_repeatedly_with_audit(database) -> None:
    order_id = create_order(database)
    now = datetime.now().astimezone().replace(tzinfo=None)
    session_id = database.start_session(
        order_id=order_id, shift_name="Schicht 1", quantity_to_process=2,
        seconds_per_piece=600, actual_started_at=now, reported_started_at=now,
        target_end=now + timedelta(minutes=20), pause_seconds=0,
    )
    first = now + timedelta(minutes=35)
    second = now + timedelta(minutes=50)
    database.extend_session(session_id, new_target_end=first, reason="Störung")
    database.extend_session(session_id, new_target_end=second, reason="Nacharbeit")
    session = database.get_session(session_id)
    extensions = database.session_extensions(session_id)
    assert session["target_end"] == second.isoformat()
    assert [item["reason"] for item in extensions] == ["Störung", "Nacharbeit"]
    assert extensions[0]["previous_target_end"] == (now + timedelta(minutes=20)).isoformat()
