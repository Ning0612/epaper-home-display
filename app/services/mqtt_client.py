from __future__ import annotations

import asyncio
import io
import json
import logging
import threading
from datetime import datetime
from typing import Callable

import paho.mqtt.client as mqtt
from PIL import Image

from app.config import MQTTConfig
from app.state import state
from app.storage.logs import log_door_event, log_face_event

logger = logging.getLogger(__name__)

_tx_log_lock = threading.Lock()

_UNKNOWN_SENTINELS = frozenset({"unknown", "no_face", "none", ""})
_ALERT_COOLDOWN_SEC = 180.0       # 3 minutes: suppress re-trigger after recent dismissal
_DOOR_REMINDER_COOLDOWN_SEC = 60.0   # 1 minute: prevent rapid re-trigger on door bounces
_FACE_EVENT_STALE_SEC = 15.0         # face event older than this is ignored for door gate
_DOOR_REMINDER_FALLBACK_TEXT = "出門注意安全"  # played when weather data has no specific warning


def _coerce_known(raw: object, identity: str) -> bool:
    if raw is not None:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.lower() not in ("false", "0", "no", "")
        return bool(raw)
    return identity.lower() not in _UNKNOWN_SENTINELS

_SUBSCRIBE_TOPICS = [
    "home/security/door",
    "home/security/face",
    "home/security/alert",
    "home/security/status",
]
_CAMERA_TOPIC = "home/security/camera"
_MAX_CAMERA_BYTES = 1_048_576   # 1 MB; QVGA JPEG is typically 15-50 KB


def make_done_callback(context: str) -> Callable[[asyncio.Future], None]:
    """Return a Future done-callback that logs errors under the given context label."""
    def _cb(f: asyncio.Future) -> None:
        if f.cancelled():
            return
        exc = f.exception()
        if exc:
            logger.error("%s error: %s", context, exc)
    return _cb


class MQTTService:
    def __init__(self, config: MQTTConfig, display_queue: asyncio.Queue, voice_service=None) -> None:
        self._config = config
        self._display_queue = display_queue
        self._voice_service = voice_service
        self._voice_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_door_reminder_at: datetime | None = None

        self._client = mqtt.Client(client_id=config.client_id)
        if config.username:
            self._client.username_pw_set(config.username, config.password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._client.connect_async(self._config.broker_host, self._config.broker_port)
        self._client.loop_start()
        logger.info("MQTT connecting to %s:%d", self._config.broker_host, self._config.broker_port)

    def stop(self) -> None:
        if self._voice_task is not None and not self._voice_task.done():
            self._voice_task.cancel()
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic: str, payload: dict) -> None:
        # agent/timestamp placed last to be authoritative; caller cannot override them
        out = {**payload, "agent": self._config.client_id, "timestamp": datetime.now().isoformat()}
        self._client.publish(topic, json.dumps(out), qos=1)
        entry = {"topic": topic, "payload": out, "sent_at": out["timestamp"]}
        with _tx_log_lock:
            state.mqtt_tx_log = [entry] + state.mqtt_tx_log[:19]

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        if rc == 0:
            state.mqtt_connected = True
            logger.info("MQTT connected")
            for topic in _SUBSCRIBE_TOPICS:
                client.subscribe(topic, qos=1)
            client.subscribe(_CAMERA_TOPIC, qos=0)
        else:
            logger.warning("MQTT connect failed rc=%d", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        state.mqtt_connected = False
        logger.warning("MQTT disconnected rc=%d", rc)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        if self._loop is None:
            return
        if msg.topic == _CAMERA_TOPIC:
            future = asyncio.run_coroutine_threadsafe(
                self._dispatch_camera(bytes(msg.payload)), self._loop
            )
            future.add_done_callback(make_done_callback("MQTT camera"))
            return
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("MQTT bad payload on %s", msg.topic)
            return
        if not isinstance(payload, dict):
            logger.warning("MQTT payload on %s is not a JSON object, ignoring", msg.topic)
            return
        future = asyncio.run_coroutine_threadsafe(
            self._dispatch(msg.topic, payload), self._loop
        )
        future.add_done_callback(make_done_callback("MQTT dispatch"))

    async def _maybe_play_door_reminder(self) -> None:
        """Play a TTS reminder when the door opens and no face (from outdoor agent) is nearby."""
        now = datetime.now()

        # Cooldown: avoid rapid re-trigger (e.g. door bounces)
        if self._last_door_reminder_at is not None:
            if (now - self._last_door_reminder_at).total_seconds() < _DOOR_REMINDER_COOLDOWN_SEC:
                logger.debug("Door reminder suppressed: within cooldown")
                return

        # Face gate: any face (known or unknown) detected recently → someone is at the door, not leaving
        face_at = state.last_face_event_at
        if face_at is not None:
            face_age = (now - face_at).total_seconds()
            if face_age <= _FACE_EVENT_STALE_SEC:
                logger.info("Door reminder skipped: face detected %.1fs ago", face_age)
                return

        from app.logic.door_reminder import generate_door_exit_text
        text = generate_door_exit_text(state.weather_current, state.weather_forecast)
        if text is None:
            logger.debug("Door reminder: no weather condition, using fallback")
            text = _DOOR_REMINDER_FALLBACK_TEXT

        if self._voice_service is not None:
            if self._voice_task is None or self._voice_task.done():
                self._last_door_reminder_at = now
                self._voice_task = asyncio.ensure_future(self._voice_service.speak(text))
                logger.info("Door reminder: %r", text)
            else:
                logger.debug("Door reminder skipped: voice busy")

    async def _dispatch_camera(self, data: bytes) -> None:
        if len(data) > _MAX_CAMERA_BYTES:
            logger.warning("Camera frame too large (%d B), skipping", len(data))
            return
        if len(data) < 2 or data[:2] != b"\xff\xd8":
            logger.debug("Camera frame missing JPEG SOI marker, skipping")
            return
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            state.last_snapshot_image = img.convert("RGB")
            state.last_camera_frame_bytes = data
            state.last_camera_frame_at = datetime.now()
        except Exception as exc:
            logger.warning("Camera frame decode failed: %s", exc)

    async def _dispatch(self, topic: str, payload: dict) -> None:
        now_str = datetime.now().isoformat()
        rx_entry = {"topic": topic, "payload": payload, "received_at": now_str}
        state.mqtt_last_rx_by_topic[topic] = rx_entry
        state.mqtt_rx_log = [rx_entry] + state.mqtt_rx_log[:49]

        if topic == "home/security/door":
            prev_door_state = (state.last_door_event or {}).get("state")
            door_state = str(payload.get("door_state") or payload.get("state") or "")[:64]
            state.last_door_event = {**payload, "state": door_state, "door_state": door_state}
            await log_door_event(door_state, payload)
            logger.info("Door: %s", door_state)
            if door_state == "open" and prev_door_state == "closed":
                await self._maybe_play_door_reminder()

        elif topic == "home/security/face":
            # Primary: vote_result (FaceGuard protocol); fallback: legacy user_name/identity fields
            raw_vote = str(payload.get("vote_result") or "").strip()[:64]
            raw_legacy = str(payload.get("user_name") or payload.get("identity") or "").strip()[:64]
            identity = raw_vote or raw_legacy or "NONE"
            known = _coerce_known(payload.get("known"), identity)
            state.last_face_event = {**payload, "identity": identity, "user_name": identity, "known": known}
            # "NONE" / "no_face" (case-insensitive) means no one present — must not gate the door reminder.
            # "UNKNOWN" means an unrecognised face was detected and SHOULD gate it.
            if identity.lower() not in ("none", "no_face"):
                state.last_face_event_at = datetime.now()
            await log_face_event(identity, known, payload)
            logger.info("Face: %s known=%s", identity, known)

        elif topic == "home/security/alert":
            state.last_alert = payload
            state.alert_face_event = state.last_face_event
            now_dt = datetime.now()

            # Cooldown: if alert page was recently dismissed and we're back on dashboard,
            # don't re-trigger within _ALERT_COOLDOWN_SEC (prevents rapid alert→dismiss→alert cycling).
            if state.display_page != "alert" and state.alert_dismissed_at is not None:
                elapsed = (now_dt - state.alert_dismissed_at).total_seconds()
                if elapsed < _ALERT_COOLDOWN_SEC:
                    logger.info(
                        "Alert suppressed within cooldown (%.0fs/%.0fs, agent=%s)",
                        elapsed, _ALERT_COOLDOWN_SEC, payload.get("agent", "?"),
                    )
                    return

            is_new_alert = state.display_page != "alert"
            if is_new_alert:
                state.alert_page_started_at = now_dt
                try:
                    self._display_queue.put_nowait("alert")
                except asyncio.QueueFull:
                    logger.debug("Display queue full, alert will render on next cycle")
            state.alert_last_triggered_at = now_dt
            state.display_page = "alert"
            if self._voice_service is not None:
                if self._voice_task is not None and not self._voice_task.done():
                    self._voice_task.cancel()  # alert preempts any lower-priority audio (e.g. door reminder)
                self._voice_task = asyncio.ensure_future(
                    self._voice_service.speak_or_play("警報！有人入侵！", "alert.wav")
                )
            logger.info(
                "Alert triggered — %s (agent=%s)",
                "new alert, switching page" if is_new_alert else "refreshing timeout",
                payload.get("agent", "?"),
            )

        elif topic == "home/security/status":
            # status is a heartbeat/general update — never treated as a security alert
            state.security_status = payload
            logger.debug("Security status update: %s", payload)
