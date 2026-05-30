from app.logic.desk_session import (
    compute_day_stats,
    format_bar,
    format_daily_summary,
    format_duration,
    format_session_end_msg,
)


def test_format_duration_zero():
    assert format_duration(0) == "0m"


def test_format_duration_negative():
    assert format_duration(-10) == "0m"


def test_format_duration_minutes_only():
    assert format_duration(2700) == "45m"


def test_format_duration_exact_hours():
    assert format_duration(7200) == "2h"


def test_format_duration_hours_and_minutes():
    assert format_duration(12000) == "3h 20m"  # 3*3600 + 20*60


def test_format_bar_no_desk():
    bar = format_bar(0, 86400, width=15)
    assert bar == "░" * 15


def test_format_bar_all_desk():
    bar = format_bar(86400, 86400, width=15)
    assert bar == "█" * 15


def test_format_bar_zero_total():
    bar = format_bar(0, 0, width=15)
    assert bar == "░" * 15


def test_format_bar_desk_ratio_38pct():
    # 38% desk: desk_chars = round(0.38 * 15) = round(5.7) = 6
    desk_sec = round(0.38 * 86400)
    bar = format_bar(desk_sec, 86400, width=15)
    assert len(bar) == 15
    assert bar.count("█") == 6
    assert bar.count("░") == 9


def test_compute_day_stats_empty():
    stats = compute_day_stats([])
    assert stats["total_seconds"] == 0
    assert stats["count"] == 0
    assert stats["longest_seconds"] == 0
    assert stats["desk_ratio"] == 0.0


def test_compute_day_stats_skips_ongoing():
    sessions = [
        {"start_ts": "2026-05-30T09:00:00", "end_ts": None, "duration_seconds": None},
    ]
    stats = compute_day_stats(sessions)
    assert stats["count"] == 0


def test_compute_day_stats_single():
    sessions = [
        {"start_ts": "2026-05-30T09:00:00", "end_ts": "2026-05-30T10:00:00", "duration_seconds": 3600},
    ]
    stats = compute_day_stats(sessions)
    assert stats["total_seconds"] == 3600
    assert stats["count"] == 1
    assert stats["longest_seconds"] == 3600


def test_compute_day_stats_multiple():
    sessions = [
        {"start_ts": "2026-05-30T09:00:00", "end_ts": "2026-05-30T10:00:00", "duration_seconds": 3600},
        {"start_ts": "2026-05-30T11:00:00", "end_ts": "2026-05-30T13:00:00", "duration_seconds": 7200},
    ]
    stats = compute_day_stats(sessions)
    assert stats["total_seconds"] == 10800
    assert stats["count"] == 2
    assert stats["longest_seconds"] == 7200
    assert abs(stats["desk_ratio"] - 10800 / 86400) < 0.001


def test_format_session_end_msg():
    session = {
        "start_ts": "2026-05-30T09:00:00",
        "end_ts": "2026-05-30T09:45:00",
        "duration_seconds": 2700,
    }
    msg = format_session_end_msg(session)
    assert "09:00" in msg
    assert "09:45" in msg
    assert "45m" in msg
    assert "書桌前時段結束" in msg


def test_format_daily_summary_structure():
    sessions = [
        {"start_ts": "2026-05-30T09:00:00", "end_ts": "2026-05-30T12:00:00", "duration_seconds": 10800},
        {"start_ts": "2026-05-30T14:00:00", "end_ts": "2026-05-30T15:10:00", "duration_seconds": 4200},
    ]
    msg = format_daily_summary("2026-05-30", sessions)
    lines = msg.strip().split("\n")
    assert len(lines) == 3
    assert lines[0] == "2026-05-30"
    assert "離開" in lines[1]
    assert "書桌前" in lines[1]
    assert "[" in lines[1] and "]" in lines[1]
    assert "次數" in lines[2]
    assert "最長一次" in lines[2]


def test_format_daily_summary_no_sessions():
    msg = format_daily_summary("2026-05-30", [])
    assert "2026-05-30" in msg
    assert "次數 0" in msg
    assert "書桌前 0m" in msg
