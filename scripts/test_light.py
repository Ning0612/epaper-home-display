"""Hardware test: MCP3008 light sensor. Run on Pi: python -m scripts.test_light"""
from __future__ import annotations

import sys
import time


def main() -> None:
    try:
        import spidev  # type: ignore[import]
    except ImportError as e:
        print(f"ERROR: {e}\nInstall: pip install spidev")
        sys.exit(1)

    spi = spidev.SpiDev()
    spi.open(0, 1)          # bus 0, CE1 (CE0 reserved for e-Paper)
    spi.max_speed_hz = 1_350_000
    channel = 0

    print("Testing MCP3008 light sensor (SPI0, CE1, ch0) ...")
    try:
        for i in range(5):
            r = spi.xfer2([1, (8 + channel) << 4, 0])
            raw = ((r[1] & 3) << 8) + r[2]
            lux = round(raw * 0.098, 1)
            bright = raw >= 500
            print(f"  [{i+1}/5] raw={raw}  ~{lux} lux  bright={bright}")
            time.sleep(1)
    finally:
        spi.close()

    print("PASS")


if __name__ == "__main__":
    main()
