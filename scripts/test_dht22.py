"""Hardware test: DHT22 sensor. Run on Pi: python -m scripts.test_dht22"""
from __future__ import annotations

import sys
import time


def main() -> None:
    try:
        import adafruit_dht  # type: ignore[import]
        import board  # type: ignore[import]
    except ImportError as e:
        print(f"ERROR: {e}\nInstall: pip install adafruit-circuitpython-dht")
        sys.exit(1)

    pin = board.D4
    print(f"Testing DHT22 on GPIO 4 ({pin}) ...")
    sensor = adafruit_dht.DHT22(pin)

    errors = 0
    for i in range(5):
        try:
            temp = sensor.temperature
            hum = sensor.humidity
            print(f"  [{i+1}/5] {temp:.1f}°C  {hum:.0f}%")
        except Exception as exc:
            errors += 1
            print(f"  [{i+1}/5] read error: {exc}")
        time.sleep(2.5)

    sensor.exit()
    if errors < 5:
        print("PASS")
    else:
        print("FAIL — all reads failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
