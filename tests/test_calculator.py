from datetime import datetime
from decimal import Decimal

from werkmate.calculator import calculate_shift_requirement
from werkmate.timecalc import standard_shift


def test_simple_calculator_for_night_shift() -> None:
    shift = standard_shift(3, datetime(2026, 8, 27).date())
    result = calculate_shift_requirement(
        total_quantity=40,
        seconds_per_piece=15 * 60,
        start=datetime(2026, 8, 27, 21, 45),
        shift_end=shift.end,
        breaks=shift.breaks,
    )
    assert result.complete_pieces == 30
    assert result.exact_pieces == Decimal("30.8")
    assert result.remaining_pieces == 10
    assert result.planned_end == datetime(2026, 8, 28, 5, 33)


def test_simple_calculator_derives_piece_time_from_total_time() -> None:
    shift = standard_shift(1, datetime(2026, 8, 27).date())
    result = calculate_shift_requirement(
        total_quantity=48,
        total_seconds=48 * 20 * 60,
        start=shift.start,
        shift_end=shift.end,
        breaks=shift.breaks,
    )
    assert result.seconds_per_piece == 20 * 60
    assert result.complete_pieces == 23
    assert result.remaining_pieces == 25
