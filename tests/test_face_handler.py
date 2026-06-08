"""Unit tests for face MQTT handler identity parsing and fmt_face display formatting."""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.config import MQTTConfig
from app.services.mqtt_client import MQTTService


def _make_service() -> MQTTService:
    cfg = MQTTConfig(broker_host="localhost", client_id="test")
    q: asyncio.Queue = asyncio.Queue()
    return MQTTService(cfg, q, voice_service=None)


async def _dispatch_face(svc: MQTTService, payload: dict, fake_state) -> None:
    with patch("app.services.mqtt_client.state", fake_state), \
         patch("app.services.mqtt_client.log_face_event", new_callable=AsyncMock), \
         patch("app.services.mqtt_client.log_door_event", new_callable=AsyncMock):
        await svc._dispatch("home/security/face", payload)


@pytest.fixture
def svc():
    return _make_service()


@pytest.fixture
def fake_state():
    from app.state import AgentState
    s = AgentState()
    s.mqtt_last_rx_by_topic = {}
    s.mqtt_rx_log = []
    return s


# --- vote_result: NONE (no face) ---

@pytest.mark.asyncio
async def test_none_clears_existing_timestamp(svc, fake_state):
    """vote_result='NONE' must clear a pre-existing last_face_event_at so the door gate passes."""
    fake_state.last_face_event_at = datetime.now()  # simulates a previous real face event
    await _dispatch_face(svc, {"vote_result": "NONE"}, fake_state)
    assert fake_state.last_face_event_at is None


# --- MQTT ordering: door open before/after NONE ---

async def _dispatch_face_open(svc, payload, fake_state):
    """Dispatch a face event while door is already 'open' in state."""
    fake_state.last_door_event = {"state": "open"}
    await _dispatch_face(svc, payload, fake_state)


@pytest.mark.asyncio
async def test_none_then_door_open_plays(svc, fake_state):
    """NONE arrives first, then door opens: gate should pass (timestamp was cleared)."""
    fake_state.last_face_event_at = datetime.now()  # stale face from before
    await _dispatch_face(svc, {"vote_result": "NONE"}, fake_state)
    # After NONE, timestamp is cleared; door gate would now pass
    assert fake_state.last_face_event_at is None


@pytest.mark.asyncio
async def test_unknown_then_door_open_then_none_retries(svc, fake_state):
    """UNKNOWN → door open (suppressed) → NONE: face handler should retry _maybe_play_door_reminder."""
    fake_state.last_face_event_at = datetime.now()  # UNKNOWN set this recently
    # Simulate door is already open when NONE arrives
    calls = []
    original = svc._maybe_play_door_reminder

    async def mock_reminder():
        calls.append(1)

    svc._maybe_play_door_reminder = mock_reminder
    await _dispatch_face_open(svc, {"vote_result": "NONE"}, fake_state)
    assert len(calls) == 1, "NONE with door open should retry _maybe_play_door_reminder"


@pytest.mark.asyncio
async def test_unknown_then_none_then_unknown_blocks(svc, fake_state):
    """UNKNOWN → NONE → UNKNOWN → door open: last UNKNOWN should still gate the reminder."""
    await _dispatch_face(svc, {"vote_result": "UNKNOWN"}, fake_state)
    await _dispatch_face(svc, {"vote_result": "NONE"}, fake_state)
    await _dispatch_face(svc, {"vote_result": "UNKNOWN"}, fake_state)
    assert fake_state.last_face_event_at is not None


@pytest.mark.asyncio
async def test_none_does_not_update_timestamp(svc, fake_state):
    """vote_result='NONE' on a fresh state also leaves last_face_event_at as None."""
    fake_state.last_face_event_at = None
    await _dispatch_face(svc, {"vote_result": "NONE"}, fake_state)
    assert fake_state.last_face_event_at is None


@pytest.mark.asyncio
async def test_none_lowercase_does_not_update_timestamp(svc, fake_state):
    """vote_result='none' (lowercase) must also not update last_face_event_at."""
    fake_state.last_face_event_at = None
    await _dispatch_face(svc, {"vote_result": "none"}, fake_state)
    assert fake_state.last_face_event_at is None


@pytest.mark.asyncio
async def test_none_known_is_false(svc, fake_state):
    """NONE identity should yield known=False."""
    await _dispatch_face(svc, {"vote_result": "NONE"}, fake_state)
    assert fake_state.last_face_event["known"] is False


# --- vote_result: UNKNOWN (unrecognised face) ---

@pytest.mark.asyncio
async def test_unknown_updates_timestamp(svc, fake_state):
    """vote_result='UNKNOWN' means a face was detected — must gate door reminder."""
    fake_state.last_face_event_at = None
    await _dispatch_face(svc, {"vote_result": "UNKNOWN"}, fake_state)
    assert fake_state.last_face_event_at is not None


@pytest.mark.asyncio
async def test_unknown_known_is_false(svc, fake_state):
    """Unrecognised face: known must be False."""
    await _dispatch_face(svc, {"vote_result": "UNKNOWN"}, fake_state)
    assert fake_state.last_face_event["known"] is False


# --- vote_result: known name ---

@pytest.mark.asyncio
async def test_known_name_updates_timestamp(svc, fake_state):
    """Known identity updates last_face_event_at."""
    fake_state.last_face_event_at = None
    await _dispatch_face(svc, {"vote_result": "alice"}, fake_state)
    assert fake_state.last_face_event_at is not None


@pytest.mark.asyncio
async def test_known_name_known_is_true(svc, fake_state):
    """Recognised name: known must be True."""
    await _dispatch_face(svc, {"vote_result": "alice"}, fake_state)
    assert fake_state.last_face_event["known"] is True


@pytest.mark.asyncio
async def test_known_name_stored_in_identity(svc, fake_state):
    """Identity is stored verbatim from vote_result."""
    await _dispatch_face(svc, {"vote_result": "bob"}, fake_state)
    assert fake_state.last_face_event["identity"] == "bob"


# --- vote_result takes priority over legacy fields ---

@pytest.mark.asyncio
async def test_vote_result_overrides_user_name(svc, fake_state):
    """vote_result wins over legacy user_name field."""
    await _dispatch_face(svc, {"vote_result": "alice", "user_name": "old_name"}, fake_state)
    assert fake_state.last_face_event["identity"] == "alice"


@pytest.mark.asyncio
async def test_legacy_user_name_used_when_vote_result_absent(svc, fake_state):
    """Falls back to user_name when vote_result is absent."""
    await _dispatch_face(svc, {"user_name": "charlie"}, fake_state)
    assert fake_state.last_face_event["identity"] == "charlie"


@pytest.mark.asyncio
async def test_legacy_identity_used_when_both_absent(svc, fake_state):
    """Falls back to identity field when vote_result and user_name are absent."""
    await _dispatch_face(svc, {"identity": "dave"}, fake_state)
    assert fake_state.last_face_event["identity"] == "dave"


@pytest.mark.asyncio
async def test_empty_payload_defaults_to_none_sentinel(svc, fake_state):
    """All fields absent: identity defaults to 'NONE', does not update timestamp."""
    fake_state.last_face_event_at = None
    await _dispatch_face(svc, {}, fake_state)
    assert fake_state.last_face_event_at is None
    assert fake_state.last_face_event["identity"] == "NONE"


# --- no_face legacy sentinel ---

@pytest.mark.asyncio
async def test_legacy_no_face_does_not_update_timestamp(svc, fake_state):
    """Legacy 'no_face' via user_name also skips timestamp update."""
    fake_state.last_face_event_at = None
    await _dispatch_face(svc, {"user_name": "no_face"}, fake_state)
    assert fake_state.last_face_event_at is None


# --- fmt_face display formatting ---

from app.display.renderer_utils import fmt_face


def _face_event(identity: str, known: bool) -> dict:
    return {"identity": identity, "known": known}


# --- fmt_face: new FaceGuard vote_result protocol ---

def test_fmt_face_no_event_returns_none():
    assert fmt_face(None) == "None"


def test_fmt_face_known_confirmed_returns_user_name():
    """KNOWN_CONFIRMED with user_name → display the user name."""
    assert fmt_face({"vote_result": "KNOWN_CONFIRMED", "user_name": "Alice"}) == "Alice"


def test_fmt_face_known_confirmed_truncates_to_8():
    assert fmt_face({"vote_result": "KNOWN_CONFIRMED", "user_name": "verylongname"}) == "verylong"


def test_fmt_face_known_confirmed_no_user_name_returns_known():
    """KNOWN_CONFIRMED without user_name falls back to 'Known'."""
    assert fmt_face({"vote_result": "KNOWN_CONFIRMED"}) == "Known"


def test_fmt_face_unknown_confirmed_returns_unknown():
    assert fmt_face({"vote_result": "UNKNOWN_CONFIRMED"}) == "Unknown"


def test_fmt_face_vote_result_none_returns_none():
    """vote_result='NONE' → display 'None'."""
    assert fmt_face({"vote_result": "NONE"}) == "None"


def test_fmt_face_vote_result_none_lowercase():
    """Lowercase 'none' is normalised to NONE enum match → 'None'."""
    assert fmt_face({"vote_result": "none"}) == "None"


# --- fmt_face: legacy identity/known fallback ---

def test_fmt_face_legacy_no_face_returns_none():
    assert fmt_face(_face_event("no_face", False)) == "None"


def test_fmt_face_empty_identity_returns_none():
    assert fmt_face(_face_event("", False)) == "None"


def test_fmt_face_legacy_none_identity_returns_none():
    """Legacy event with identity='NONE' falls through to legacy path → 'None'."""
    assert fmt_face(_face_event("NONE", False)) == "None"


def test_fmt_face_legacy_none_lowercase():
    assert fmt_face(_face_event("none", False)) == "None"


def test_fmt_face_unknown_returns_unknown():
    """Legacy vote_result='UNKNOWN' identity → 'Unknown'."""
    assert fmt_face(_face_event("UNKNOWN", False)) == "Unknown"


def test_fmt_face_unknown_without_known_field():
    """'UNKNOWN' identity without known field also displays 'Unknown' (defensive)."""
    assert fmt_face({"identity": "UNKNOWN"}) == "Unknown"


def test_fmt_face_known_name_returns_name():
    assert fmt_face(_face_event("alice", True)) == "alice"


def test_fmt_face_name_truncated_to_8():
    assert fmt_face(_face_event("verylongname", True)) == "verylong"
