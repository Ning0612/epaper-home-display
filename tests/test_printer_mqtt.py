import asyncio
import json
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt

from app.config import PrinterConfig
from app.services.printer_mqtt import BambuMQTTService
from app.state import state


def test_unconfigured_does_not_build_client_or_connect():
    config = PrinterConfig(host="", serial="", access_code="")
    loop = object()

    with patch("app.services.printer_mqtt.mqtt.Client") as client_cls:
        service = BambuMQTTService(config)
        service.start(loop)

    client_cls.assert_not_called()
    assert service._client is None
    assert service._loop is loop


def test_build_client_sets_bambu_tls_and_credentials():
    client = MagicMock()
    config = PrinterConfig(host="printer.local", serial="SERIAL123", access_code="secret")

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client) as client_cls:
        service = BambuMQTTService(config)

    client_cls.assert_called_once_with(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="epaper-bambu-SERIAL123",
    )
    client.username_pw_set.assert_called_once_with("bblp", "secret")
    client.tls_set.assert_called_once()
    assert client.tls_set.call_args.kwargs["cert_reqs"] is not None
    client.tls_insecure_set.assert_called_once_with(True)
    assert client.on_connect == service._on_connect
    assert client.on_message == service._on_message
    assert client.on_disconnect == service._on_disconnect


def test_on_connect_subscribes_report_and_publishes_pushall():
    client = MagicMock()
    config = PrinterConfig(host="printer.local", serial="SERIAL123", access_code="secret")

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client):
        service = BambuMQTTService(config)

    state.printer_broker_connected = False
    service._on_connect(client, None, None, 0)

    assert state.printer_broker_connected is True
    client.subscribe.assert_called_once_with("device/SERIAL123/report", qos=0)
    client.publish.assert_called_once_with(
        "device/SERIAL123/request",
        json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}),
    )


def test_stale_disconnect_callback_is_ignored():
    old_client = MagicMock()
    new_client = MagicMock()
    old_config = PrinterConfig(host="old", serial="OLD", access_code="secret")
    new_config = PrinterConfig(host="new", serial="NEW", access_code="secret")

    with patch("app.services.printer_mqtt.mqtt.Client", side_effect=[old_client, new_client]):
        service = BambuMQTTService(old_config)
        service._loop = object()
        service.update_config(new_config)

    state.printer_broker_connected = True
    service._on_disconnect(old_client, None, 1)
    assert state.printer_broker_connected is True

    service._on_disconnect(new_client, None, 1)
    assert state.printer_broker_connected is False


def test_update_config_unconfigured_to_configured_connects_on_existing_loop():
    client = MagicMock()
    old_config = PrinterConfig()
    new_config = PrinterConfig(host="printer.local", port=8883, serial="SERIAL123", access_code="secret")
    loop = object()

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client):
        service = BambuMQTTService(old_config)
        service._loop = loop
        service.update_config(new_config)

    assert service._config is new_config
    assert service._client is client
    client.connect_async.assert_called_once_with("printer.local", 8883)
    client.loop_start.assert_called_once_with()


def test_update_config_configured_to_unconfigured_stops_without_new_client():
    old_client = MagicMock()
    old_config = PrinterConfig(host="printer.local", serial="SERIAL123", access_code="secret")
    new_config = PrinterConfig(host="", serial="", access_code="")
    loop = object()

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=old_client) as client_cls:
        service = BambuMQTTService(old_config)
        service._loop = loop
        service.update_config(new_config)

    assert client_cls.call_count == 1
    old_client.disconnect.assert_called_once_with()
    old_client.loop_stop.assert_called_once_with()
    assert service._client is None
    assert state.printer_broker_connected is False


def test_handle_report_updates_only_non_none_fields():
    service = BambuMQTTService(PrinterConfig())
    state.printer_pct = 0.1
    state.printer_remaining_min = 50
    state.printer_task_name = "old.3mf"
    state.printer_gcode_state = "RUNNING"

    asyncio.run(service._handle_report({"print": {"mc_percent": 30, "mc_remaining_time": -1}}))

    assert state.printer_pct == 0.3
    assert state.printer_remaining_min == 50
    assert state.printer_task_name == "old.3mf"
    assert state.printer_gcode_state == "RUNNING"
    assert state.printer_updated_at is not None
