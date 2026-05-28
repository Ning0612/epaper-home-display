"""Hardware test: MQTT broker connectivity. Run on Pi: python -m scripts.test_mqtt"""
from __future__ import annotations

import json
import sys
import threading
import time

import paho.mqtt.client as mqtt

from app.config import load_settings


def main() -> None:
    settings = load_settings()
    host = settings.mqtt.broker_host
    port = settings.mqtt.broker_port

    print(f"Testing MQTT broker at {host}:{port} ...")

    received: list[dict] = []
    connected = threading.Event()

    client = mqtt.Client(client_id="epaper-test-probe")

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print("  Connected")
            connected.set()
            c.subscribe("epaper/test", qos=1)
        else:
            print(f"  Connect failed rc={rc}")

    def on_message(c, userdata, msg):
        payload = json.loads(msg.payload.decode())
        received.append(payload)
        print(f"  Received: {payload}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port)
    client.loop_start()

    if not connected.wait(timeout=5):
        print("FAIL — could not connect to broker")
        client.loop_stop()
        sys.exit(1)

    test_payload = {"agent": "epaper-test", "value": 42}
    client.publish("epaper/test", json.dumps(test_payload), qos=1)
    print("  Published test message")

    time.sleep(2)
    client.loop_stop()
    client.disconnect()

    if received:
        print("PASS")
    else:
        print("FAIL — no message received (broker may not loopback)")
        sys.exit(1)


if __name__ == "__main__":
    main()
