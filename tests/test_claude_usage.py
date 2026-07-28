import json

from app.loops.claude_usage import _backoff_seconds
from app.services.claude_usage import ClaudeUsageService, _parse_retry_after, _parse_usage


def test_load_credentials_accepts_access_and_refresh_token(tmp_path):
    creds_path = tmp_path / "claude_creds.json"
    creds_path.write_text(
        json.dumps({"access_token": "access-fake", "refresh_token": "refresh-fake"}),
        encoding="utf-8",
    )

    service = ClaudeUsageService(str(creds_path))

    assert service.load_credentials() is True
    assert service._creds == {"access_token": "access-fake", "refresh_token": "refresh-fake"}


def test_load_credentials_accepts_claude_code_nested_camelcase(tmp_path):
    creds_path = tmp_path / "claude_creds.json"
    creds_path.write_text(
        json.dumps({"claudeAiOauth": {"accessToken": "a-fake", "refreshToken": "r-fake"}}),
        encoding="utf-8",
    )

    service = ClaudeUsageService(str(creds_path))

    assert service.load_credentials() is True
    assert service._creds == {"access_token": "a-fake", "refresh_token": "r-fake"}


def test_load_credentials_rejects_access_token_only(tmp_path):
    """A `claude setup-token` credential has no refresh_token, and its token lacks the
    `user:profile` scope this endpoint requires — accepting it would 403 on every poll."""
    creds_path = tmp_path / "claude_creds.json"
    creds_path.write_text(json.dumps({"access_token": "sk-ant-oat01-fake"}), encoding="utf-8")

    service = ClaudeUsageService(str(creds_path))

    assert service.load_credentials() is False


def test_load_credentials_missing_file_returns_false(tmp_path):
    service = ClaudeUsageService(str(tmp_path / "does_not_exist.json"))

    assert service.load_credentials() is False


def test_parse_retry_after_reads_delta_seconds():
    assert _parse_retry_after("164") == 164
    assert _parse_retry_after("  30 ") == 30


def test_parse_retry_after_ignores_unusable_values():
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("") is None
    assert _parse_retry_after("0") is None
    assert _parse_retry_after("-5") is None
    assert _parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None


def test_backoff_waits_out_a_cooldown_longer_than_the_poll_interval():
    # The bug this guards: Retry-After 164s with a 60s poll interval used to retry
    # at 60s, inside the cooldown, earning another 429 forever.
    assert _backoff_seconds(60, 164) == 169


def test_backoff_keeps_poll_interval_when_cooldown_is_shorter():
    assert _backoff_seconds(600, 30) == 600


def test_backoff_falls_back_to_poll_interval_without_retry_after():
    assert _backoff_seconds(60, None) == 60


def test_backoff_is_capped():
    assert _backoff_seconds(60, 99999) == 3600


def test_parse_usage_basic():
    data = _parse_usage(
        {
            "five_hour": {"utilization": 49.0, "resets_at": "2026-07-28T20:30:00+00:00"},
            "seven_day": {"utilization": 56.0, "resets_at": "2026-07-29T20:00:00+00:00"},
        }
    )

    assert data is not None
    assert data.usage_5h == 0.49
    assert data.usage_7d == 0.56
