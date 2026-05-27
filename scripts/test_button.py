"""Hardware test: GPIO button. Run on Pi: python -m scripts.test_button"""
from __future__ import annotations

import sys
import time


def main() -> None:
    try:
        import RPi.GPIO as GPIO  # type: ignore[import]
    except ImportError as e:
        print(f"ERROR: {e}\nInstall: pip install RPi.GPIO")
        sys.exit(1)

    PIN = 17
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print(f"Testing button on GPIO {PIN} — press within 10 seconds ...")

    pressed = False

    def on_press(channel):
        nonlocal pressed
        pressed = True
        print("  Button pressed!")

    GPIO.add_event_detect(PIN, GPIO.FALLING, callback=on_press, bouncetime=200)

    for _ in range(20):
        if pressed:
            break
        time.sleep(0.5)

    GPIO.cleanup()

    if pressed:
        print("PASS")
    else:
        print("TIMEOUT — button not pressed")
        sys.exit(1)


if __name__ == "__main__":
    main()
