from argparse import Namespace
from datetime import datetime

from werkmate.cli import build_parser, format_duration, run, warn_unusual_end


def test_duration_format() -> None:
    assert format_duration(7_332) == "02:02:12"


def test_unusual_end_requires_warning() -> None:
    session = {
        "reported_started_at": "2026-08-26T13:45:00",
        "target_end": "2026-08-26T18:00:00",
    }
    assert warn_unusual_end(session, datetime(2026, 8, 26, 18, 20)) is None
    assert "30 Minuten" in warn_unusual_end(session, datetime(2026, 8, 26, 19))
    assert "vor der Anmeldezeit" in warn_unusual_end(
        session, datetime(2026, 8, 26, 13)
    )


def test_cli_smoke_flow(tmp_path, capsys) -> None:
    database_path = tmp_path / "werkmate.sqlite3"
    parser = build_parser()
    assert run(parser.parse_args([
        "--db", str(database_path), "auftrag-neu", "--nummer", "FA-9",
        "--gesenk", "8720", "--arbeitsgang", "FP1", "--menge", "4",
        "--minuten", "7,5",
    ])) == 0
    assert "Auftrag angelegt" in capsys.readouterr().out

    assert run(parser.parse_args([
        "--db", str(database_path), "start", "--auftrag", "1", "--menge", "4",
        "--anmeldung", "2026-08-26 06:00", "--schicht", "1",
    ])) == 0
    assert "Soll-Ende 2026-08-26 06:30" in capsys.readouterr().out

    assert run(parser.parse_args([
        "--db", str(database_path), "rueckmelden", "--einsatz", "1", "--stueck", "3",
        "--abmeldung", "2026-08-26 06:30", "--notiz", "Ein Stück bleibt offen",
    ])) == 0
    assert "offen 1 Stück" in capsys.readouterr().out

    assert run(parser.parse_args([
        "--db", str(database_path), "historie",
    ])) == 0
    output = capsys.readouterr().out
    assert "3 Stück" in output
    assert "Ein Stück bleibt offen" in output

