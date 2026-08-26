from werkmate.database import WerkMateDatabase


def test_catalog_stores_multiple_operations_for_one_die(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    database.save_standard(
        die_number="8720",
        operation_code="FP1",
        operation_name="Fertigputzen 1",
        seconds_per_piece=1_200,
        die_description="Beispielgesenk",
    )
    database.save_standard(
        die_number="8720",
        operation_code="KR",
        operation_name="Kantenrunden",
        seconds_per_piece=270,
        die_description="Beispielgesenk",
    )
    standards = database.standards_for_die("8720")
    assert [item["operation_code"] for item in standards] == ["FP1", "KR"]
    assert standards[1]["seconds_per_piece"] == 270


def test_updating_standard_does_not_create_duplicate(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    first_id = database.save_standard(
        die_number="8720", operation_code="FP1", operation_name="Fertigputzen 1",
        seconds_per_piece=1_200,
    )
    second_id = database.save_standard(
        die_number="8720", operation_code="fp1", operation_name="Fertigputzen neu",
        seconds_per_piece=1_080,
    )
    assert second_id == first_id
    assert database.standards_for_die("8720")[0]["seconds_per_piece"] == 1_080
    assert database.standards_for_die("8720")[0]["operation_name"] == "Fertigputzen neu"


def test_catalog_search_and_deactivation(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    standard_id = database.save_standard(
        die_number="9120", operation_code="KR", operation_name="Kantenrunden",
        seconds_per_piece=450, die_description="Großes Gesenk",
    )
    assert len(database.list_catalog(search="Groß")) == 1
    assert len(database.list_catalog(search="Kanten")) == 1
    database.deactivate_standard(standard_id)
    assert database.list_catalog() == []
    assert len(database.list_catalog(include_inactive=True)) == 1
    assert database.standards_for_die("9120") == []


def test_optional_operation_name_falls_back_to_code(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    database.save_standard(
        die_number="8720", operation_code="fp", operation_name="",
        seconds_per_piece=1_200,
    )
    standard = database.standards_for_die("8720")[0]
    assert standard["operation_code"] == "FP"
    assert standard["operation_name"] == "FP"
