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
async def test_none_does_not_update_timestamp(svc, fake_state):
    """vote_result='NONE' must not update last_face_event_at."""
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


def test_fmt_face_no_event_returns_none():
    assert fmt_face(None) == "NONE"


def test_fmt_face_vote_result_none_returns_none():
    """vote_result='NONE' stored as identity='NONE' → display 'NONE', not 'Unknown'."""
    assert fmt_face(_face_event("NONE", False)) == "NONE"


def test_fmt_face_none_lowercase():
    assert fmt_face(_face_event("none", False)) == "NONE"


def test_fmt_face_legacy_no_face_returns_none():
    assert fmt_face(_face_event("no_face", False)) == "NONE"


def test_fmt_face_empty_identity_returns_none():
    assert fmt_face(_face_event("", False)) == "NONE"


def test_fmt_face_unknown_returns_unknown():
    """vote_result='UNKNOWN' → face detected but unrecognized → 'Unknown'."""
    assert fmt_face(_face_event("UNKNOWN", False)) == "Unknown"


def test_fmt_face_unknown_without_known_field():
    """'UNKNOWN' identity without known field also displays 'Unknown' (defensive)."""
    assert fmt_face({"identity": "UNKNOWN"}) == "Unknown"


def test_fmt_face_known_name_returns_name():
    assert fmt_face(_face_event("alice", True)) == "alice"


def test_fmt_face_name_truncated_to_8():
    assert fmt_face(_face_event("verylongname", True)) == "verylong"
