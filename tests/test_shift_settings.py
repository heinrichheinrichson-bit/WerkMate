from datetime import datetime

import pytest

from werkmate.database import WerkMateDatabase
from werkmate.service import WerkMateService


def test_custom_shift_and_pause_are_used_for_new_calculations(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    database.save_shift_settings([
        {"shift_number": 1, "start_time": "06:00", "end_time": "14:00",
         "break_start": "09:00", "break_end": "09:30"},
        {"shift_number": 2, "start_time": "14:00", "end_time": "22:00",
         "break_start": "18:00", "break_end": "18:30"},
        {"shift_number": 3, "start_time": "22:00", "end_time": "06:00",
         "break_start": "02:00", "break_end": "02:30"},
    ])
    service = WerkMateService(database)

    early = service.shift_for_start(1, datetime(2026, 8, 26, 6))
    assert early.end == datetime(2026, 8, 26, 14)
    assert early.breaks[0].start == datetime(2026, 8, 26, 9)
    night = service.shift_for_start(3, datetime(2026, 8, 27, 2))
    assert night.start == datetime(2026, 8, 26, 22)
    assert night.end == datetime(2026, 8, 27, 6)
    assert night.breaks[0].start == datetime(2026, 8, 27, 2)


def test_pause_outside_shift_is_rejected(tmp_path) -> None:
    database = WerkMateDatabase(tmp_path / "db.sqlite3")
    settings = database.shift_settings()
    settings[0]["break_start"] = "15:00"
    settings[0]["break_end"] = "15:15"
    with pytest.raises(ValueError, match="Pause"):
        database.save_shift_settings(settings)
