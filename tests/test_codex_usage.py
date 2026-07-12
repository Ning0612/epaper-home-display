import pytest

from app.services.codex_usage import _parse_usage


def test_weekly_primary_window_without_secondary_is_not_reported_as_5h():
    data = _parse_usage(
        {
            "rate_limit": {
                "primary_window": {
                    "used_percent": 2,
                    "limit_window_seconds": 604800,
                    "reset_at": 1784487944,
                },
                "secondary_window": None,
            }
        }
    )

    assert data is not None
    assert data.usage_5h is None
    assert data.usage_7d == 0.02
    assert data.reset_5h == "--:--"


def test_windows_are_assigned_by_duration():
    data = _parse_usage(
        {
            "rate_limit": {
                "primary_window": {
                    "used_percent": 25,
                    "limit_window_seconds": 18000,
                },
                "secondary_window": {
                    "used_percent": 75,
                    "limit_window_seconds": 604800,
                },
            }
        }
    )

    assert data is not None
    assert data.usage_5h == 0.25
    assert data.usage_7d == 0.75


def test_missing_window_duration_falls_back_to_wire_position():
    data = _parse_usage(
        {
            "rate_limits": {
                "primary": {"used_percent": 11},
                "secondary": {"used_percent": 33},
            }
        }
    )

    assert data is not None
    assert data.usage_5h == 0.11
    assert data.usage_7d == 0.33


def test_same_short_duration_falls_back_to_wire_positions_without_dropping_data():
    data = _parse_usage(
        {
            "rate_limits": {
                "primary": {"used_percent": 11, "limit_window_seconds": 18000, "reset_at": 100},
                "secondary": {"used_percent": 33, "limit_window_seconds": 18000, "reset_at": 200},
            }
        }
    )

    assert data is not None
    assert data.usage_5h == 0.11
    assert data.usage_7d == 0.33
    assert data.reset_5h != "--:--"
    assert data.reset_7d != "--:--"


def test_same_long_duration_falls_back_to_wire_positions_without_dropping_data():
    data = _parse_usage(
        {
            "rate_limits": {
                "primary": {"used_percent": 11, "limit_window_seconds": 604800, "reset_at": 100},
                "secondary": {"used_percent": 33, "limit_window_seconds": 604800, "reset_at": 200},
            }
        }
    )

    assert data is not None
    assert data.usage_5h == 0.11
    assert data.usage_7d == 0.33
    assert data.reset_5h != "--:--"
    assert data.reset_7d != "--:--"


def test_window_duration_boundary_classifies_by_duration_not_wire_position():
    # primary/secondary are swapped relative to their duration so this only
    # passes if classification is truly duration-driven, not a positional
    # fallback that happens to agree with duration for this input.
    data = _parse_usage(
        {
            "rate_limits": {
                "primary": {"used_percent": 33, "limit_window_seconds": 43201},
                "secondary": {"used_percent": 11, "limit_window_seconds": 43200},
            }
        }
    )

    assert data is not None
    assert data.usage_5h == 0.11
    assert data.usage_7d == 0.33


def test_boolean_window_duration_is_not_treated_as_a_real_duration():
    # bool is an int subclass in Python; limit_window_seconds=False must not
    # be misread as a 0-second (short) window via the numeric comparison —
    # it should fall back to the secondary window's positional default (long).
    data = _parse_usage(
        {
            "rate_limits": {
                "secondary": {"used_percent": 11, "limit_window_seconds": False},
            }
        }
    )

    assert data is not None
    assert data.usage_5h is None
    assert data.usage_7d == 0.11


def test_non_numeric_window_duration_falls_back_to_wire_position():
    data = _parse_usage(
        {
            "rate_limits": {
                "primary": {"used_percent": 11, "limit_window_seconds": "604800"},
                "secondary": {"used_percent": 33, "limit_window_seconds": 604800},
            }
        }
    )

    assert data is not None
    assert data.usage_5h == 0.11
    assert data.usage_7d == 0.33


@pytest.mark.parametrize("body", [{}, {"other": "value"}])
def test_missing_rate_limit_data_returns_none_usage_values(body):
    data = _parse_usage(body)

    assert data is not None
    assert data.usage_5h is None
    assert data.usage_7d is None
