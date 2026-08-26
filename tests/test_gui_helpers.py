from werkmate.gui import display_time


def test_display_time_uses_german_order() -> None:
    assert display_time("2026-08-26T13:45:00") == "26.08.2026 13:45"
    assert display_time(None) == "–"

