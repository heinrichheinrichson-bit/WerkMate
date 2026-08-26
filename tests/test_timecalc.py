from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from werkmate.models import BreakWindow, Order
from werkmate.timecalc import (
    add_productive_duration,
    minutes_to_seconds,
    possible_complete_pieces,
    productive_duration_between,
    remaining_or_overdue,
    standard_shift,
    target_end,
)


def dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, day, hour, minute)


def test_decimal_minutes_with_german_comma() -> None:
    assert minutes_to_seconds("7,5") == 450
    assert minutes_to_seconds(Decimal("8.25")) == 495


def test_order_calculates_open_quantity_and_time() -> None:
    order = Order("FA-1", "8720", "FP1", 24, 1_200, completed_quantity=20)
    assert order.open_quantity == 4
    assert order.open_target_duration == timedelta(minutes=80)


def test_end_without_pause() -> None:
    assert target_end(dt(26, 6), 3, 1_200) == dt(26, 7)


def test_full_pause_moves_target_end() -> None:
    pause = BreakWindow(dt(26, 8, 45), dt(26, 9, 3))
    assert target_end(dt(26, 8), 1, 5_400, (pause,)) == dt(26, 9, 48)


def test_starting_inside_pause_uses_remaining_part_only() -> None:
    pause = BreakWindow(dt(26, 8, 45), dt(26, 9, 3))
    assert add_productive_duration(dt(26, 8, 55), timedelta(minutes=20), (pause,)) == dt(26, 9, 23)


def test_ending_exactly_at_pause_start_adds_no_pause() -> None:
    pause = BreakWindow(dt(26, 8, 45), dt(26, 9, 3))
    assert add_productive_duration(dt(26, 8), timedelta(minutes=45), (pause,)) == dt(26, 8, 45)


def test_productive_shift_time_is_462_minutes() -> None:
    shift = standard_shift(2, date(2026, 8, 26))
    assert productive_duration_between(shift.start, shift.end, shift.breaks) == timedelta(minutes=462)


def test_night_shift_crosses_midnight() -> None:
    shift = standard_shift(3, date(2026, 8, 26))
    assert shift.start == dt(26, 21, 45)
    assert shift.end == dt(27, 5, 45)
    assert shift.breaks[0].start == dt(27, 1, 45)


def test_complete_pieces_until_shift_end() -> None:
    pieces, remainder, next_piece_overtime = possible_complete_pieces(
        dt(26, 18), dt(26, 21, 45), 1_200
    )
    assert pieces == 11
    assert remainder == timedelta(minutes=5)
    assert next_piece_overtime == timedelta(minutes=15)


def test_exact_fit_means_an_additional_piece_needs_full_piece_time() -> None:
    pieces, remainder, overtime = possible_complete_pieces(
        dt(26, 20, 45), dt(26, 21, 45), 1_200
    )
    assert pieces == 3
    assert remainder == timedelta(0)
    assert overtime == timedelta(minutes=20)


def test_remaining_and_overdue_are_positive() -> None:
    assert remaining_or_overdue(dt(26, 18), dt(26, 17, 45)) == (
        "verbleibend",
        timedelta(minutes=15),
    )
    assert remaining_or_overdue(dt(26, 18), dt(26, 18, 12)) == (
        "ueberzogen",
        timedelta(minutes=12),
    )


@pytest.mark.parametrize("bad", ["0", "-2", "abc"])
def test_invalid_minutes_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        minutes_to_seconds(bad)

