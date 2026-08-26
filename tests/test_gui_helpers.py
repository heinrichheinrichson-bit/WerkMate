from datetime import datetime
from decimal import Decimal

from werkmate.gui import (
    current_shift_number,
    display_time,
    format_piece_equivalent,
    format_total_target_time,
)


def test_display_time_uses_german_order() -> None:
    assert display_time("2026-08-26T13:45:00") == "26.08.2026 13:45"
    assert display_time(None) == "–"


def test_piece_equivalent_uses_one_decimal_and_german_comma() -> None:
    assert format_piece_equivalent(Decimal("23.1")) == "23,1"
    assert format_piece_equivalent(Decimal("11.25")) == "11,3"


def test_current_shift_is_recognized() -> None:
    assert current_shift_number(datetime(2026, 8, 26, 5, 45)) == 1
    assert current_shift_number(datetime(2026, 8, 26, 13, 45)) == 2
    assert current_shift_number(datetime(2026, 8, 26, 23, 0)) == 3


def test_total_target_time_shows_minutes_and_hours() -> None:
    assert format_total_target_time(48 * 20 * 60) == "960,0 min (16 h 00 min)"
