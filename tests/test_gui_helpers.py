from datetime import date, datetime
from decimal import Decimal

from werkmate.gui import (
    current_shift_number,
    display_time,
    format_piece_equivalent,
    format_total_target_time,
    parse_plan_start,
    parse_plan_start_override,
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


def test_plan_start_override_accepts_clock_time_and_rolls_to_next_day() -> None:
    plan_start = datetime(2026, 8, 26, 21, 0)
    assert parse_plan_start_override("21:30", plan_start) == datetime(2026, 8, 26, 21, 30)
    assert parse_plan_start_override("13:45", plan_start) == datetime(2026, 8, 27, 13, 45)


def test_plan_start_override_accepts_full_timestamp() -> None:
    plan_start = datetime(2026, 8, 26, 5, 45)
    assert parse_plan_start_override("2026-08-27 06:00", plan_start) == datetime(2026, 8, 27, 6)


def test_plan_start_accepts_clock_time_on_current_day() -> None:
    assert parse_plan_start("13:45", date(2026, 8, 26)) == datetime(2026, 8, 26, 13, 45)


def test_plan_start_keeps_full_timestamp_compatibility() -> None:
    assert parse_plan_start("2026-08-27 05:45") == datetime(2026, 8, 27, 5, 45)
