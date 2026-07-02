import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt

from app.config import PrinterConfig
from app.services.printer_mqtt import BAMBULAB_CLOUD_MQTT_HOST, BAMBULAB_CLOUD_MQTT_PORT, BambuMQTTService
from app.state import state


def _write_creds(base: Path, case, *, access_token="token", uid="12345", serial="SERIAL123"):
    case_dir = base / case
    case_dir.mkdir(parents=True, exist_ok=True)
    creds_path = case_dir / "bambu_creds.json"
    creds_path.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "uid": uid,
                "serial": serial,
            }
        ),
        encoding="utf-8",
    )
    return creds_path


def _config(*, creds_path, serial=""):
    return PrinterConfig(serial=serial, creds_path=str(creds_path))


def test_missing_creds_does_not_build_client_or_connect(tmp_path):
    config = _config(creds_path=tmp_path / "missing" / "missing.json")
    loop = object()

    with patch("app.services.printer_mqtt.mqtt.Client") as client_cls:
        service = BambuMQTTService(config)
        service.start(loop)

    client_cls.assert_not_called()
    assert service._client is None
    assert service._loop is loop


def test_invalid_creds_does_not_build_client(tmp_path):
    creds_path = tmp_path / "invalid" / "bambu_creds.json"
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    creds_path.write_text(json.dumps({"access_token": "token", "uid": "12345"}), encoding="utf-8")
    config = _config(creds_path=creds_path)

    with patch("app.services.printer_mqtt.mqtt.Client") as client_cls:
        service = BambuMQTTService(config)

    client_cls.assert_not_called()
    assert service._client is None


def test_build_client_sets_bambu_cloud_tls_and_credentials(tmp_path):
    client = MagicMock()
    creds_path = _write_creds(tmp_path, "build", access_token="cloud-token", uid="98765", serial="SERIAL123")
    config = _config(creds_path=creds_path)

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client) as client_cls:
        service = BambuMQTTService(config)

    client_cls.assert_called_once_with(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="epaper-bambu-SERIAL123",
    )
    client.username_pw_set.assert_called_once_with("u_98765", "cloud-token")
    client.tls_set.assert_called_once_with()
    client.tls_insecure_set.assert_not_called()
    assert client.on_connect == service._on_connect
    assert client.on_message == service._on_message
    assert client.on_disconnect == service._on_disconnect


def test_config_serial_overrides_creds_serial(tmp_path):
    client = MagicMock()
    creds_path = _write_creds(tmp_path, "override", serial="CREDSERIAL")
    config = _config(creds_path=creds_path, serial="OVERRIDE")

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client):
        service = BambuMQTTService(config)

    assert service._serial == "OVERRIDE"
    client.username_pw_set.assert_called_once_with("u_12345", "token")


def test_start_connects_to_fixed_bambu_cloud_broker(tmp_path):
    client = MagicMock()
    creds_path = _write_creds(tmp_path, "start")
    config = _config(creds_path=creds_path)
    loop = object()

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client):
        service = BambuMQTTService(config)
        service.start(loop)

    client.connect_async.assert_called_once_with(BAMBULAB_CLOUD_MQTT_HOST, BAMBULAB_CLOUD_MQTT_PORT)
    client.loop_start.assert_called_once_with()


def test_on_connect_subscribes_report_and_publishes_pushall(tmp_path):
    client = MagicMock()
    creds_path = _write_creds(tmp_path, "connect", serial="SERIAL123")
    config = _config(creds_path=creds_path)

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


def test_stale_disconnect_callback_is_ignored(tmp_path):
    old_client = MagicMock()
    new_client = MagicMock()
    old_creds = _write_creds(tmp_path, "stale_old", serial="OLD")
    new_creds = _write_creds(tmp_path, "stale_new", serial="NEW")
    old_config = _config(creds_path=old_creds)
    new_config = _config(creds_path=new_creds)

    with patch("app.services.printer_mqtt.mqtt.Client", side_effect=[old_client, new_client]):
        service = BambuMQTTService(old_config)
        service._loop = object()
        service.update_config(new_config)

    state.printer_broker_connected = True
    service._on_disconnect(old_client, None, 1)
    assert state.printer_broker_connected is True

    service._on_disconnect(new_client, None, 1)
    assert state.printer_broker_connected is False


def test_update_config_unconfigured_to_configured_connects_on_existing_loop(tmp_path):
    client = MagicMock()
    old_config = _config(creds_path=tmp_path / "update_missing" / "missing.json")
    creds_path = _write_creds(tmp_path, "update_new", serial="SERIAL123")
    new_config = _config(creds_path=creds_path)
    loop = object()

    with patch("app.services.printer_mqtt.mqtt.Client", return_value=client):
        service = BambuMQTTService(old_config)
        service._loop = loop
        service.update_config(new_config)

    assert service._config is new_config
    assert service._client is client
    client.connect_async.assert_called_once_with(BAMBULAB_CLOUD_MQTT_HOST, BAMBULAB_CLOUD_MQTT_PORT)
    client.loop_start.assert_called_once_with()


def test_update_config_configured_to_unconfigured_stops_without_new_client(tmp_path):
    old_client = MagicMock()
    old_creds = _write_creds(tmp_path, "update_old", serial="SERIAL123")
    old_config = _config(creds_path=old_creds)
    new_config = _config(creds_path=tmp_path / "update_stop_missing" / "missing.json")
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


def test_handle_report_updates_only_non_none_fields(tmp_path):
    service = BambuMQTTService(_config(creds_path=tmp_path / "handle_missing" / "missing.json"))
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
