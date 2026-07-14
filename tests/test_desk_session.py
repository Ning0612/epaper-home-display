from datetime import datetime, timedelta, timezone

import pytest

from app.logic.desk_session import (
    aggregate_sessions_by_day,
    compute_day_stats,
    format_bar,
    format_daily_summary,
    format_daily_summary_embed,
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


def test_aggregate_sessions_by_day_splits_cross_midnight_session():
    days = aggregate_sessions_by_day(
        [
            {
                "start_ts": "2024-12-31T23:00:00",
                "end_ts": "2025-01-01T02:30:00",
                "duration_seconds": 12600,
            }
        ],
        2025,
    )

    assert len(days) == 365
    assert days[0]["date"] == "2025-01-01"
    assert days[0]["total_seconds"] == 9000
    assert days[0]["status"] == "recorded"
    assert days[-1]["total_seconds"] == 0


def test_aggregate_sessions_by_day_includes_ongoing_session_until_now():
    days = aggregate_sessions_by_day(
        [{"start_ts": "2024-02-29T23:30:00", "end_ts": None, "duration_seconds": None}],
        2024,
        now=datetime(2024, 3, 1, 1, 15),
    )

    assert len(days) == 366
    assert days[59]["total_seconds"] == 1800
    assert days[60]["total_seconds"] == 4500
    assert days[59]["status"] == "recorded"
    assert days[60]["status"] == "ongoing"


def test_aggregate_sessions_by_day_ignores_invalid_and_out_of_range_sessions():
    days = aggregate_sessions_by_day(
        [
            {"start_ts": "not-a-date", "end_ts": "2025-01-01T01:00:00", "duration_seconds": 3600},
            {"start_ts": "2025-01-02T09:00:00", "end_ts": "not-a-date", "duration_seconds": 3600},
            {"start_ts": "2026-01-01T00:00:00", "end_ts": "2026-01-01T01:00:00", "duration_seconds": 3600},
            {"start_ts": "2024-01-01T00:00:00", "end_ts": "2024-01-01T01:00:00", "duration_seconds": 3600},
        ],
        2025,
    )

    assert sum(day["total_seconds"] for day in days) == 0


def test_aggregate_sessions_by_day_converts_offset_aware_timestamps():
    days = aggregate_sessions_by_day(
        [{"start_ts": "2025-01-01T23:30:00-05:00", "end_ts": "2025-01-02T00:30:00-05:00"}],
        2025,
        now=datetime(2025, 1, 3, tzinfo=timezone.utc),
        timezone_name="Asia/Taipei",
    )

    assert days[1]["date"] == "2025-01-02"
    assert days[1]["total_seconds"] == 3600


def test_aggregate_sessions_by_day_uses_legacy_timezone_for_naive_rows():
    days = aggregate_sessions_by_day(
        [{"start_ts": "2025-01-01T23:30:00", "end_ts": "2025-01-02T00:30:00"}],
        2025,
        now=datetime(2025, 1, 3, tzinfo=timezone.utc),
        timezone_name="Asia/Taipei",
        legacy_timezone=timezone(timedelta(hours=-5)),
    )

    assert days[1]["date"] == "2025-01-02"
    assert days[1]["total_seconds"] == 3600


def test_aggregate_sessions_by_day_respects_dst_offset():
    days = aggregate_sessions_by_day(
        [{"start_ts": "2025-03-09T01:30:00-05:00", "end_ts": "2025-03-09T03:30:00-04:00"}],
        2025,
        now=datetime(2025, 3, 10, tzinfo=timezone.utc),
        timezone_name="America/New_York",
    )

    assert days[67]["date"] == "2025-03-09"
    assert days[67]["total_seconds"] == 3600


def test_aggregate_sessions_by_day_respects_dst_fall_back_fold():
    days = aggregate_sessions_by_day(
        [{"start_ts": "2025-11-02T01:30:00-04:00", "end_ts": "2025-11-02T01:15:00-05:00"}],
        2025,
        now=datetime(2025, 11, 3, tzinfo=timezone.utc),
        timezone_name="America/New_York",
    )

    day = next(day for day in days if day["date"] == "2025-11-02")
    assert day["total_seconds"] == 2700
    assert day["status"] == "recorded"


def test_aggregate_sessions_by_day_uses_now_for_ongoing_even_with_stale_duration():
    days = aggregate_sessions_by_day(
        [{"start_ts": "2025-06-01T09:00:00", "end_ts": None, "duration_seconds": 60}],
        2025,
        now=datetime(2025, 6, 1, 10, 0),
    )

    assert days[151]["total_seconds"] == 3600
    assert days[151]["status"] == "ongoing"


def test_aggregate_sessions_by_day_merges_overlapping_sessions():
    days = aggregate_sessions_by_day(
        [
            {"start_ts": "2025-06-02T09:00:00", "end_ts": "2025-06-02T10:00:00"},
            {"start_ts": "2025-06-02T09:30:00", "end_ts": "2025-06-02T11:00:00"},
        ],
        2025,
    )

    assert days[152]["total_seconds"] == 7200
    assert days[152]["session_count"] == 2


def test_aggregate_sessions_by_day_marks_future_days():
    days = aggregate_sessions_by_day([], 2025, now=datetime(2025, 6, 1, 12, 0))

    assert days[151]["status"] == "empty"
    assert days[152]["status"] == "future"


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


def test_compute_day_stats_skips_invalid_negative_duration():
    sessions = [
        {"start_ts": "2026-05-30T09:00:00", "end_ts": "2026-05-30T08:59:00", "duration_seconds": -60},
        {"start_ts": "2026-05-30T10:00:00", "end_ts": "2026-05-30T10:30:00", "duration_seconds": 1800},
    ]
    stats = compute_day_stats(sessions)
    assert stats["count"] == 1
    assert stats["total_seconds"] == 1800


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


def test_format_daily_summary_embed_uses_l2_contract():
    sessions = [
        {"start_ts": "2026-05-30T09:00:00", "end_ts": "2026-05-30T12:00:00", "duration_seconds": 10800},
        {"start_ts": "2026-05-30T14:00:00", "end_ts": "2026-05-30T15:10:00", "duration_seconds": 4200},
    ]
    payload = format_daily_summary_embed("2026-05-30", sessions)
    embed = payload["embeds"][0]
    assert embed["title"] == "📊 在席日報 · 2026-05-30"
    assert embed["description"].startswith("🟥⬜⬜⬜⬜⬜⬜⬜⬜⬜  17%")
    assert len(embed["fields"]) == 3
    assert all(field["inline"] is True for field in embed["fields"])
    assert embed["color"] == 15158332


def test_format_daily_summary_embed_caps_over_target_at_999_percent():
    payload = format_daily_summary_embed(
        "2026-05-30",
        [{"start_ts": "2026-05-30T00:00:00", "end_ts": "2026-05-31T02:00:00", "duration_seconds": 93600}],
    )
    embed = payload["embeds"][0]
    assert "🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩  108%" in embed["description"]
    assert embed["color"] == 3066993


@pytest.mark.parametrize(
    ("percent", "color", "block"),
    [
        (49, 15158332, "🟥"),
        (50, 15132194, "🟨"),
        (79, 15132194, "🟨"),
        (80, 3447003, "🟦"),
        (99, 3447003, "🟦"),
        (100, 3066993, "🟩"),
    ],
)
def test_format_daily_summary_embed_uses_style_guide_boundaries(percent, color, block):
    payload = format_daily_summary_embed(
        "2026-05-30",
        [{"duration_seconds": percent * 864, "start_ts": "2026-05-30T00:00:00", "end_ts": "2026-05-30T01:00:00"}],
    )
    embed = payload["embeds"][0]
    assert embed["color"] == color
    assert embed["description"].startswith(block)
