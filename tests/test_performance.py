from werkmate.performance import (
    calculate_performance,
    format_quantity_performance,
    format_time_performance,
)


def completed_session(*, end: str, completed: int) -> dict:
    return {
        "status": "abgeschlossen",
        "reported_ended_at": end,
        "target_end": "2026-08-26T10:00:00",
        "quantity_to_process": 10,
        "completed_quantity": completed,
        "seconds_per_piece": 600,
    }


def test_delay_and_more_pieces_are_calculated() -> None:
    result = calculate_performance(
        completed_session(end="2026-08-26T10:20:00", completed=12)
    )
    assert result.time_delta_seconds == 1_200
    assert result.time_delta_percent == 20
    assert result.quantity_delta == 2
    assert result.quantity_delta_percent == 20
    assert format_time_performance(result) == "🔴 20,0 min Verzug (+20,0 %)"
    assert format_quantity_performance(result) == "🟢 +2 Stück (+20,0 %)"


def test_early_finish_and_fewer_pieces_are_calculated() -> None:
    result = calculate_performance(
        completed_session(end="2026-08-26T09:45:00", completed=8)
    )
    assert result.time_delta_seconds == -900
    assert result.quantity_delta == -2
    assert format_time_performance(result) == "🟢 15,0 min früher (15,0 %)"
    assert format_quantity_performance(result) == "🔴 -2 Stück (-20,0 %)"


def test_cancelled_and_running_sessions_are_not_rated() -> None:
    assert calculate_performance({"status": "abgebrochen"}) is None
    assert calculate_performance({"status": "laufend"}) is None
    assert format_time_performance(None) == "–"
    assert format_quantity_performance(None) == "–"
