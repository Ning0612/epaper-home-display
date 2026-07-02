from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from app.config import _AP_STATUS_FILE
from app.state import state

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


async def _wifi_monitor_loop(display_queue: asyncio.Queue, settings: "Settings") -> None:
    """Detect WiFi mode (client vs AP) and update state accordingly.

    On startup reads the status file written by wifi_manager.sh, then re-checks
    every monitor_interval seconds so the display transitions automatically when
    the user connects via the portal and AP mode ends.
    """
    await _check_and_update(display_queue, settings)

    while True:
        await asyncio.sleep(settings.wifi.monitor_interval)
        try:
            await _check_and_update(display_queue, settings)
        except Exception as exc:
            logger.error("wifi_monitor error: %s", exc)


async def _check_and_update(display_queue: asyncio.Queue, settings: "Settings") -> None:
    prev_mode = state.wifi_mode
    new_mode, ssid, password, ip = await _detect_mode(settings)

    state.wifi_mode = new_mode
    state.ap_ssid = ssid
    state.ap_password = password
    state.ap_ip = ip

    if new_mode == "ap":
        # Always enforce ap_mode page while in AP — this repairs the page if some
        # other event changed display_page away from ap_mode.
        if state.display_page != "ap_mode":
            prev_page = state.display_page
            state.display_page = "ap_mode"
            logger.info("AP mode active (prev_page=%s), restoring ap_mode display", prev_page)
            try:
                display_queue.put_nowait("wifi_ap_mode")
            except asyncio.QueueFull:
                pass
        elif prev_mode != "ap":
            logger.info("Entering AP mode: SSID=%s IP=%s", ssid, ip)

    elif prev_mode == "ap":
        # AP ended (user connected via portal, or manual intervention)
        state.display_page = "dashboard"
        logger.info("AP mode ended, returning to dashboard")
        try:
            display_queue.put_nowait("wifi_connected")
        except asyncio.QueueFull:
            pass


async def _detect_mode(settings: "Settings") -> tuple[str, str, str, str]:
    """Return (mode, ssid, password, ip).  mode is 'ap' | 'client' | 'unknown'."""
    if os.path.exists(_AP_STATUS_FILE):
        try:
            with open(_AP_STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("mode") == "ap":
                return (
                    "ap",
                    data.get("ssid", settings.wifi.ap_ssid),
                    data.get("password", settings.wifi.ap_password),
                    data.get("ip", "10.42.0.1"),
                )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read AP status file: %s", exc)

    try:
        connected = await asyncio.to_thread(_check_wifi_connected)
        return ("client" if connected else "unknown"), "", "", ""
    except Exception as exc:
        logger.debug("nmcli check failed: %s", exc)
        return "unknown", "", "", ""


def _check_wifi_connected() -> bool:
    """Return True if wlan0 is connected as a client (not AP)."""
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "TYPE,STATE", "dev"],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        )
        return any(
            line.startswith("wifi:connected")
            for line in out.splitlines()
        )
    except FileNotFoundError:
        # nmcli not available (dev environment / Windows)
        return True
    except subprocess.CalledProcessError:
        return False
