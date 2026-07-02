from app.logic.hydration import parse_status


def test_parse_status_normal_case():
    result = parse_status({
        "current_ml": 1200,
        "goal_ml": 2000,
        "pct": 0.6,
        "event": "drink",
        "device_time": "2026-07-02T14:32:10+08:00",
    })
    assert result is not None
    assert result.current_ml == 1200
    assert result.goal_ml == 2000
    assert result.pct == 0.6
    assert result.event == "drink"


def test_parse_status_calculates_missing_pct():
    result = parse_status({"current_ml": 500, "goal_ml": 2000, "event": "heartbeat"})
    assert result is not None
    assert result.pct == 0.25


def test_parse_status_goal_zero_has_no_pct():
    result = parse_status({"current_ml": 500, "goal_ml": 0, "pct": 0.5})
    assert result is not None
    assert result.pct is None


def test_parse_status_missing_goal_is_invalid():
    assert parse_status({"current_ml": 500}) is None


def test_parse_status_missing_current_is_invalid():
    assert parse_status({"goal_ml": 2000}) is None


def test_parse_status_negative_current_is_invalid():
    assert parse_status({"current_ml": -100, "goal_ml": 2000}) is None


def test_parse_status_negative_goal_is_invalid():
    assert parse_status({"current_ml": 100, "goal_ml": -2000}) is None


def test_parse_status_bool_current_is_invalid():
    assert parse_status({"current_ml": True, "goal_ml": 2000}) is None


def test_parse_status_nan_pct_is_dropped_not_crashed():
    result = parse_status({"current_ml": 500, "goal_ml": 2000, "pct": float("nan")})
    assert result is not None
    # pct treated as missing -> falls back to current/goal
    assert result.pct == 0.25


def test_parse_status_infinite_pct_is_dropped_not_crashed():
    result = parse_status({"current_ml": 500, "goal_ml": 2000, "pct": float("inf")})
    assert result is not None
    assert result.pct == 0.25


def test_parse_status_float_integer_current_is_accepted():
    result = parse_status({"current_ml": 500.0, "goal_ml": 2000.0})
    assert result is not None
    assert result.current_ml == 500
    assert result.goal_ml == 2000


def test_parse_status_nan_current_is_invalid():
    assert parse_status({"current_ml": float("nan"), "goal_ml": 2000}) is None


def test_parse_status_implausibly_large_current_is_invalid():
    assert parse_status({"current_ml": 100000, "goal_ml": 2000}) is None


def test_parse_status_at_upper_bound_is_accepted():
    result = parse_status({"current_ml": 9999, "goal_ml": 9999})
    assert result is not None
    assert result.current_ml == 9999


def test_parse_status_huge_finite_pct_is_dropped_not_overflowed():
    # 1e308 is finite (passes math.isfinite) but pct*100 overflows to inf downstream —
    # must be rejected at parse time, not just filtered for NaN/Infinity.
    result = parse_status({"current_ml": 500, "goal_ml": 2000, "pct": 1e308})
    assert result is not None
    assert result.pct == 0.25
