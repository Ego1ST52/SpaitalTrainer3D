from datetime import date, timedelta

from logic.daily import DAILY_MODES, daily_done, daily_task
from logic.training_code import parse_code

DAY = date(2026, 11, 12)


def test_same_day_same_task():
    assert daily_task(DAY) == daily_task(DAY)


def test_code_is_valid_and_matches_task():
    mode, level, seed, code = daily_task(DAY)
    assert parse_code(code) == (mode, level, seed)


def test_modes_cycle_through_all():
    modes = {daily_task(DAY + timedelta(days=i))[0] for i in range(len(DAILY_MODES))}
    assert modes == set(DAILY_MODES)


def test_harder_at_weekend():
    monday = DAY - timedelta(days=DAY.weekday())
    assert daily_task(monday)[1] == "easy"
    assert daily_task(monday + timedelta(days=6))[1] == "hard"


def test_done_only_with_todays_code_today():
    code = daily_task(DAY)[3]
    played = {"code": code, "played_at": "2026-11-12T18:00:00"}
    assert daily_done([played], DAY)
    assert not daily_done([{**played, "played_at": "2026-11-11T18:00:00"}], DAY)
    assert not daily_done([{**played, "code": "11-0000"}], DAY)
    assert not daily_done([{"code": None, "played_at": "2026-11-12T10:00:00"}], DAY)
