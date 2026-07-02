from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import Awaitable, Callable

import paho.mqtt.client as mqtt

from app.config import MQTTConfig
from app.logic.hydration import parse_status
from app.state import state

logger = logging.getLogger(__name__)

_STATUS_TOPIC = "hydracup/status"
_AVAILABILITY_TOPIC = "hydracup/availability"

_Handler = Callable[[dict], Awaitable[None]]


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
    def __init__(self, config: MQTTConfig) -> None:
        self._config = config
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._handlers: dict[str, _Handler] = {
            _STATUS_TOPIC: self._handle_status,
            _AVAILABILITY_TOPIC: self._handle_availability,
        }

        self._client = self._build_client(config)

    def _build_client(self, config: MQTTConfig) -> mqtt.Client:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=config.client_id,
        )
        if config.username:
            client.username_pw_set(config.username, config.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        return client

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._loop = loop
            self._client.connect_async(self._config.broker_host, self._config.broker_port)
            self._client.loop_start()
            logger.info("HydraCup MQTT connecting to %s:%d", self._config.broker_host, self._config.broker_port)

    def stop(self) -> None:
        with self._lock:
            self._client.disconnect()
            self._client.loop_stop()
            self._loop = None

    def update_config(self, config: MQTTConfig) -> None:
        """Reconnect using new broker/credential settings (called after a WebUI settings save)."""
        with self._lock:
            loop = self._loop  # capture before rebuilding — stopping the old client clears it
            if loop is not None:
                self._client.disconnect()
                self._client.loop_stop()

            self._config = config
            self._client = self._build_client(config)

            if loop is not None:
                self._loop = loop
                self._client.connect_async(config.broker_host, config.broker_port)
                self._client.loop_start()
                logger.info("HydraCup MQTT reconnecting to %s:%d", config.broker_host, config.broker_port)

    # NOTE: `client is not self._client` is a best-effort guard against stale
    # callbacks from a client already replaced by update_config(). It closes the
    # common case (callback arrives after the swap) but not a narrow TOCTOU window
    # where a callback passes this check on the paho thread microseconds before
    # update_config() swaps self._client on the main thread. Same guard is used in
    # _on_disconnect() and _on_message(). Accepted trade-off for a single-user home
    # dashboard: worst case is state.hydra_broker_connected, hydra_device_online, or
    # hydra_current_ml/hydra_goal_ml/hydra_pct/hydra_updated_at briefly reflecting a
    # stale client/message, self-corrected by the next real callback or message.
    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        if client is not self._client:
            return  # stale callback from a client replaced by update_config()
        if rc == 0:
            state.hydra_broker_connected = True
            logger.info("HydraCup MQTT connected")
            for topic in self._handlers:
                client.subscribe(topic, qos=1)
        else:
            state.hydra_broker_connected = False
            logger.warning("HydraCup MQTT connect failed rc=%d", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        if client is not self._client:
            return  # stale callback from a client replaced by update_config()
        state.hydra_broker_connected = False
        logger.warning("HydraCup MQTT disconnected rc=%d", rc)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        if client is not self._client:
            return  # stale callback from a client replaced by update_config()
        if self._loop is None:
            return
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("HydraCup MQTT bad payload on %s: %s", msg.topic, exc)
            return
        if not isinstance(payload, dict):
            logger.warning("HydraCup MQTT payload on %s is not a JSON object, ignoring", msg.topic)
            return

        future = asyncio.run_coroutine_threadsafe(self._dispatch(msg.topic, payload), self._loop)
        future.add_done_callback(make_done_callback("HydraCup MQTT dispatch"))

    async def _dispatch(self, topic: str, payload: dict) -> None:
        handler = self._handlers.get(topic)
        if handler is None:
            logger.debug("HydraCup MQTT ignoring unhandled topic %s", topic)
            return
        await handler(payload)

    async def _handle_status(self, payload: dict) -> None:
        parsed = parse_status(payload)
        if parsed is None:
            logger.warning("HydraCup status payload invalid, ignoring: %s", payload)
            return
        state.hydra_current_ml = parsed.current_ml
        state.hydra_goal_ml = parsed.goal_ml
        state.hydra_pct = parsed.pct
        state.hydra_updated_at = datetime.now()
        logger.debug("HydraCup status updated event=%s", parsed.event)

    async def _handle_availability(self, payload: dict) -> None:
        online = payload.get("online")
        if not isinstance(online, bool):
            logger.warning("HydraCup availability payload invalid, ignoring: %s", payload)
            return
        state.hydra_device_online = online
        logger.info("HydraCup device %s", "online" if online else "offline")
