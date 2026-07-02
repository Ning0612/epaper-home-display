from __future__ import annotations

import asyncio
import json
import logging
import ssl
import threading
from datetime import datetime

import paho.mqtt.client as mqtt

from app.config import PrinterConfig
from app.logic.printer import parse_print_status
from app.services.mqtt_client import make_done_callback
from app.state import state

logger = logging.getLogger(__name__)


class BambuMQTTService:
    def __init__(self, config: PrinterConfig) -> None:
        self._config = config
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._client: mqtt.Client | None = self._build_client(config)

    def _is_configured(self, config: PrinterConfig) -> bool:
        return bool(config.host and config.serial and config.access_code)

    def _report_topic(self) -> str:
        return f"device/{self._config.serial}/report"

    def _request_topic(self) -> str:
        return f"device/{self._config.serial}/request"

    def _build_client(self, config: PrinterConfig) -> mqtt.Client | None:
        if not self._is_configured(config):
            return None
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=f"epaper-bambu-{config.serial}",
        )
        client.username_pw_set("bblp", config.access_code)
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        return client

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._loop = loop
            if self._client is None:
                state.printer_broker_connected = False
                logger.info("Bambu printer not configured, skipping connection")
                return
            self._client.connect_async(self._config.host, self._config.port)
            self._client.loop_start()
            logger.info("Bambu printer MQTT connecting to %s:%d", self._config.host, self._config.port)

    def stop(self) -> None:
        with self._lock:
            if self._client is not None:
                self._client.disconnect()
                self._client.loop_stop()
            self._loop = None
            state.printer_broker_connected = False

    def update_config(self, config: PrinterConfig) -> None:
        """Reconnect using new Bambu printer LAN MQTT settings."""
        with self._lock:
            loop = self._loop
            old_client = self._client
            if old_client is not None and loop is not None:
                old_client.disconnect()
                old_client.loop_stop()

            self._config = config
            self._client = self._build_client(config)
            state.printer_broker_connected = False

            if loop is not None:
                self._loop = loop
                if self._client is None:
                    logger.info("Bambu printer not configured, skipping connection")
                    return
                self._client.connect_async(config.host, config.port)
                self._client.loop_start()
                logger.info("Bambu printer MQTT reconnecting to %s:%d", config.host, config.port)

    # NOTE: `client is not self._client` is a best-effort guard against stale
    # callbacks from a client already replaced by update_config(). It closes the
    # common case (callback arrives after the swap) but not a narrow TOCTOU window
    # where a callback passes this check on the paho thread microseconds before
    # update_config() swaps self._client on the main thread. Same guard is used in
    # _on_disconnect() and _on_message(). Accepted trade-off for a single-user home
    # dashboard: worst case is state.printer_broker_connected, printer_pct,
    # printer_remaining_min, printer_task_name, printer_gcode_state, or
    # printer_updated_at briefly reflecting a stale client/message, self-corrected
    # by the next real callback or message.
    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        if client is not self._client:
            return
        if rc == 0:
            state.printer_broker_connected = True
            logger.info("Bambu printer MQTT connected")
            client.subscribe(self._report_topic(), qos=0)
            client.publish(
                self._request_topic(),
                json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}),
            )
        else:
            state.printer_broker_connected = False
            logger.warning("Bambu printer MQTT connect failed rc=%d", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        if client is not self._client:
            return
        state.printer_broker_connected = False
        logger.warning("Bambu printer MQTT disconnected rc=%d", rc)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        if client is not self._client:
            return
        if self._loop is None:
            return
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Bambu printer MQTT bad payload on %s: %s", msg.topic, exc)
            return
        if not isinstance(payload, dict):
            logger.warning("Bambu printer MQTT payload on %s is not a JSON object, ignoring", msg.topic)
            return

        future = asyncio.run_coroutine_threadsafe(self._handle_report(payload), self._loop)
        future.add_done_callback(make_done_callback("Bambu printer MQTT dispatch"))

    async def _handle_report(self, payload: dict) -> None:
        print_obj = payload.get("print")
        if not isinstance(print_obj, dict):
            return
        parsed = parse_print_status(print_obj)
        if parsed is None:
            return
        if parsed.pct is not None:
            state.printer_pct = parsed.pct
        if parsed.remaining_min is not None:
            state.printer_remaining_min = parsed.remaining_min
        if parsed.task_name is not None:
            state.printer_task_name = parsed.task_name
        if parsed.gcode_state is not None:
            state.printer_gcode_state = parsed.gcode_state
        state.printer_updated_at = datetime.now()
