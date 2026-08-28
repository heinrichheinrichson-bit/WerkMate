from datetime import datetime, timedelta

from werkmate.simple_work import clock, next_clock_datetime


def test_clock_formats_countdown_and_overtime() -> None:
    assert clock(timedelta(hours=2, minutes=3, seconds=4)) == "02:03:04"


def test_new_alarm_time_can_cross_midnight() -> None:
    now = datetime(2026, 8, 28, 23, 30)
    assert next_clock_datetime("01:15", now) == datetime(2026, 8, 29, 1, 15)
