"""Tests for alert dispatch behavior, button alarm commands, and camera limits."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import MQTTConfig
from app.services.mqtt_client import MQTTService, _MAX_CAMERA_BYTES


def _make_service() -> MQTTService:
    cfg = MQTTConfig(broker_host="localhost", client_id="test")
    q: asyncio.Queue = asyncio.Queue()
    return MQTTService(cfg, q, voice_service=None)


@pytest.fixture
def svc():
    return _make_service()


@pytest.fixture
def fake_state():
    from app.state import AgentState
    s = AgentState()
    s.mqtt_last_rx_by_topic = {}
    s.mqtt_rx_log = []
    s.alert_wake_event = asyncio.Event()
    return s


async def _dispatch_alert(svc, payload, fake_state):
    with patch("app.services.mqtt_client.state", fake_state), \
         patch("app.services.mqtt_client.log_door_event", new_callable=AsyncMock), \
         patch("app.services.mqtt_client.log_face_event", new_callable=AsyncMock):
        await svc._dispatch("home/security/alert", payload)


# --- alert accepted: state updates ---

@pytest.mark.asyncio
async def test_alert_accepted_sets_last_alert(svc, fake_state):
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    # `is` is intentional: presence loop uses object identity for dedup (_last_processed_alert)
    assert fake_state.last_alert is payload


@pytest.mark.asyncio
async def test_alert_accepted_records_received_at(svc, fake_state):
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    before = datetime.now()
    await _dispatch_alert(svc, payload, fake_state)
    after = datetime.now()
    assert fake_state.last_alert_received_at is not None
    assert before <= fake_state.last_alert_received_at <= after


@pytest.mark.asyncio
async def test_alert_accepted_wakes_presence_loop(svc, fake_state):
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    assert not fake_state.alert_wake_event.is_set()
    await _dispatch_alert(svc, payload, fake_state)
    assert fake_state.alert_wake_event.is_set()


@pytest.mark.asyncio
async def test_alert_snapshots_face_event(svc, fake_state):
    """alert_face_event must be a snapshot (copy), not a live reference."""
    face = {"vote_result": "KNOWN_CONFIRMED", "user_name": "Alice", "known": True}
    fake_state.last_face_event = face
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    # Snapshot is a copy — mutating original does not affect the snapshot
    face["user_name"] = "Changed"
    assert fake_state.alert_face_event["user_name"] == "Alice"


@pytest.mark.asyncio
async def test_alert_with_no_face_event_snapshots_none(svc, fake_state):
    fake_state.last_face_event = None
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_RED", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    assert fake_state.alert_face_event is None


# --- cooldown suppression ---

@pytest.mark.asyncio
async def test_cooldown_suppressed_alert_does_not_update_last_alert(svc, fake_state):
    """Alert within cooldown window must NOT update state.last_alert."""
    fake_state.display_page = "dashboard"
    fake_state.alert_dismissed_at = datetime.now()  # just dismissed
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    assert fake_state.last_alert is None


@pytest.mark.asyncio
async def test_cooldown_suppressed_alert_does_not_set_wake_event(svc, fake_state):
    fake_state.display_page = "dashboard"
    fake_state.alert_dismissed_at = datetime.now()
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    assert not fake_state.alert_wake_event.is_set()


@pytest.mark.asyncio
async def test_cooldown_expired_alert_is_accepted(svc, fake_state):
    """Alert outside cooldown window should be accepted."""
    fake_state.display_page = "dashboard"
    fake_state.alert_dismissed_at = datetime.now() - timedelta(seconds=200)  # well past 180s
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_YELLOW", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    assert fake_state.last_alert is payload  # identity intentional (see dedup note above)


@pytest.mark.asyncio
async def test_cooldown_bypassed_when_already_on_alert_page(svc, fake_state):
    """When already on alert page, cooldown is bypassed regardless of alert_dismissed_at."""
    fake_state.display_page = "alert"
    fake_state.alert_dismissed_at = datetime.now()  # just dismissed, but page is already alert
    payload = {"agent": "FaceGuard", "alert_level": "ALERT_RED", "alert_type": "UNKNOWN_CONFIRMED"}
    await _dispatch_alert(svc, payload, fake_state)
    # Cooldown bypass: alert must be accepted and wake event must be set
    assert fake_state.last_alert is payload
    assert fake_state.alert_wake_event.is_set()


# --- camera frame size ---

def test_max_camera_bytes_matches_spec():
    """Ensure the limit is set correctly (64KB = small buffer above 48KB spec)."""
    assert _MAX_CAMERA_BYTES == 64 * 1024


@pytest.mark.asyncio
async def test_camera_frame_too_large_is_rejected(svc, fake_state):
    sentinel = object()
    fake_state.last_snapshot_image = sentinel  # pre-seed so None != rejection
    oversized = b"\xff\xd8" + b"\x00" * (64 * 1024)
    with patch("app.services.mqtt_client.state", fake_state):
        await svc._dispatch_camera(oversized)
    assert fake_state.last_snapshot_image is sentinel  # unchanged — frame was actively rejected


@pytest.mark.asyncio
async def test_camera_frame_within_limit_is_accepted(svc, fake_state):
    import io
    from PIL import Image
    img = Image.new("RGB", (10, 10), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    frame = buf.getvalue()
    assert len(frame) < 64 * 1024
    with patch("app.services.mqtt_client.state", fake_state):
        await svc._dispatch_camera(frame)
    assert fake_state.last_snapshot_image is not None


# --- button alarm commands ---

@pytest.mark.asyncio
async def test_button3_trigger_from_dashboard_publishes(fake_state):
    """Button 3 must publish TRIGGER_ALARM even when not on alert page."""
    from app.loops.button import _handle_btn_trigger_alarm
    fake_state.display_page = "dashboard"
    mock_mqtt = MagicMock()
    with patch("app.loops.button.state", fake_state):
        await _handle_btn_trigger_alarm(None, mock_mqtt)
    mock_mqtt.publish.assert_called_once()
    call_args = mock_mqtt.publish.call_args
    assert call_args[0][0] == "home/home_state/alarm_command"
    assert call_args[0][1]["alarm_decision"] == "TRIGGER_ALARM"


@pytest.mark.asyncio
async def test_button3_trigger_from_alert_page_publishes(fake_state):
    from app.loops.button import _handle_btn_trigger_alarm
    fake_state.display_page = "alert"
    mock_mqtt = MagicMock()
    with patch("app.loops.button.state", fake_state):
        await _handle_btn_trigger_alarm(None, mock_mqtt)
    mock_mqtt.publish.assert_called_once()
    call_args = mock_mqtt.publish.call_args
    assert call_args[0][0] == "home/home_state/alarm_command"
    assert call_args[0][1]["alarm_decision"] == "TRIGGER_ALARM"


@pytest.mark.asyncio
async def test_button4_cancel_from_dashboard_publishes(fake_state):
    """Button 4 must publish CANCEL_ALARM even when not on alert page."""
    from app.loops.button import _handle_btn_cancel_alarm
    fake_state.display_page = "dashboard"
    mock_mqtt = MagicMock()
    with patch("app.loops.button.state", fake_state):
        await _handle_btn_cancel_alarm(mock_mqtt)
    mock_mqtt.publish.assert_called_once()
    call_args = mock_mqtt.publish.call_args
    assert call_args[0][0] == "home/home_state/alarm_command"
    assert call_args[0][1]["alarm_decision"] == "CANCEL_ALARM"


@pytest.mark.asyncio
async def test_button3_on_alert_page_extends_timeout(fake_state):
    """Button 3 on alert page must update alert_last_triggered_at."""
    from app.loops.button import _handle_btn_trigger_alarm
    fake_state.display_page = "alert"
    fake_state.alert_last_triggered_at = None
    mock_mqtt = MagicMock()
    with patch("app.loops.button.state", fake_state):
        await _handle_btn_trigger_alarm(None, mock_mqtt)
    assert fake_state.alert_last_triggered_at is not None


@pytest.mark.asyncio
async def test_button3_off_alert_page_does_not_set_triggered_at(fake_state):
    """Button 3 from dashboard must NOT update alert_last_triggered_at."""
    from app.loops.button import _handle_btn_trigger_alarm
    fake_state.display_page = "dashboard"
    fake_state.alert_last_triggered_at = None
    mock_mqtt = MagicMock()
    with patch("app.loops.button.state", fake_state):
        await _handle_btn_trigger_alarm(None, mock_mqtt)
    assert fake_state.alert_last_triggered_at is None
