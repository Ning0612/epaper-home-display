from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt

from app.config import MQTTConfig
from app.services.mqtt_client import MQTTService


def test_init_builds_client_with_credentials():
    client = MagicMock()
    config = MQTTConfig(client_id="test-client", username="user", password="secret")

    with patch("app.services.mqtt_client.mqtt.Client", return_value=client) as client_cls:
        service = MQTTService(config)

    client_cls.assert_called_once_with(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        client_id="test-client",
    )
    client.username_pw_set.assert_called_once_with("user", "secret")
    assert client.on_connect == service._on_connect
    assert client.on_message == service._on_message
    assert client.on_disconnect == service._on_disconnect


def test_init_skips_credentials_for_blank_username():
    client = MagicMock()

    with patch("app.services.mqtt_client.mqtt.Client", return_value=client):
        MQTTService(MQTTConfig(username="", password="secret"))

    client.username_pw_set.assert_not_called()


def test_update_config_before_start_rebuilds_client_without_connecting():
    old_client = MagicMock()
    new_client = MagicMock()
    old_config = MQTTConfig(broker_host="old-host", client_id="old-client")
    new_config = MQTTConfig(broker_host="new-host", broker_port=2883, client_id="new-client")

    with patch("app.services.mqtt_client.mqtt.Client", side_effect=[old_client, new_client]):
        service = MQTTService(old_config)
        service.update_config(new_config)

    assert service._config is new_config
    assert service._client is new_client
    old_client.disconnect.assert_not_called()
    old_client.loop_stop.assert_not_called()
    new_client.connect_async.assert_not_called()
    new_client.loop_start.assert_not_called()


def test_update_config_after_start_reconnects_new_client_on_existing_loop():
    old_client = MagicMock()
    new_client = MagicMock()
    old_config = MQTTConfig(broker_host="old-host", broker_port=1883, client_id="old-client")
    new_config = MQTTConfig(broker_host="new-host", broker_port=2883, client_id="new-client")
    loop = object()

    with patch("app.services.mqtt_client.mqtt.Client", side_effect=[old_client, new_client]):
        service = MQTTService(old_config)
        service._loop = loop
        service.update_config(new_config)

    assert service._loop is loop
    assert service._config is new_config
    assert service._client is new_client
    old_client.disconnect.assert_called_once_with()
    old_client.loop_stop.assert_called_once_with()
    new_client.connect_async.assert_called_once_with("new-host", 2883)
    new_client.loop_start.assert_called_once_with()


def test_stop_clears_loop_so_later_update_config_does_not_reconnect():
    old_client = MagicMock()
    new_client = MagicMock()
    config = MQTTConfig(broker_host="host", client_id="client")
    new_config = MQTTConfig(broker_host="new-host", client_id="new-client")
    loop = object()

    with patch("app.services.mqtt_client.mqtt.Client", side_effect=[old_client, new_client]):
        service = MQTTService(config)
        service._loop = loop
        service.stop()
        assert service._loop is None

        service.update_config(new_config)

    assert service._loop is None
    new_client.connect_async.assert_not_called()
    new_client.loop_start.assert_not_called()


def test_stale_callback_from_replaced_client_is_ignored():
    old_client = MagicMock()
    new_client = MagicMock()
    config = MQTTConfig(broker_host="host", client_id="old")
    new_config = MQTTConfig(broker_host="host", client_id="new")

    with patch("app.services.mqtt_client.mqtt.Client", side_effect=[old_client, new_client]):
        service = MQTTService(config)
        service._loop = object()
        service.update_config(new_config)  # old_client is now stale; new_client is current

        from app.state import state
        state.hydra_broker_connected = True

        # A late callback arriving from the replaced (old) client must be ignored
        service._on_disconnect(old_client, None, 1)
        assert state.hydra_broker_connected is True

        # A callback from the current client is still handled normally
        service._on_disconnect(new_client, None, 1)
        assert state.hydra_broker_connected is False
