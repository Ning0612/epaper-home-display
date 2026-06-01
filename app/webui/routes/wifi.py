from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.config import _AP_STATUS_FILE, _WIFI_SCAN_CACHE_FILE
from app.state import state
from app.webui.templates.wifi import _WIFI_HTML

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

# Prevent concurrent nmcli calls (scan up to 20s, connect up to 30s).
_nmcli_lock = asyncio.Lock()


class _WifiConnectBody(BaseModel):
    ssid: str
    password: str = ""  # empty = open network


def create_wifi_router(settings: "Settings") -> APIRouter:
    router = APIRouter()

    @router.get("/wifi", response_class=HTMLResponse)
    async def wifi_page():
        """AP mode WiFi setup portal — no authentication required."""
        return HTMLResponse(_WIFI_HTML)

    @router.get("/api/wifi/scan")
    async def wifi_scan():
        """Scan nearby WiFi networks, sorted by signal strength (descending).

        Only functional when the device is in AP mode.  Returns 503 otherwise
        so clients know the portal is inactive.
        """
        if state.wifi_mode != "ap":
            raise HTTPException(503, detail="裝置不在 AP 設定模式")
        if _nmcli_lock.locked():
            raise HTTPException(429, detail="WiFi 操作中，請稍後再試")
        try:
            async with _nmcli_lock:
                networks = await asyncio.to_thread(_scan_wifi_sync)
            return JSONResponse({"networks": networks})
        except Exception as exc:
            logger.error("WiFi scan failed: %s", exc)
            raise HTTPException(500, detail=f"WiFi 掃描失敗：{exc}")

    @router.post("/api/wifi/connect")
    async def wifi_connect(body: _WifiConnectBody):
        """Connect to a WiFi network.

        Only functional when the device is in AP mode.  On success, removes
        the AP status file so wifi_monitor transitions the display back to
        dashboard mode within monitor_interval seconds.
        """
        if state.wifi_mode != "ap":
            raise HTTPException(503, detail="裝置不在 AP 設定模式")
        if _nmcli_lock.locked():
            raise HTTPException(429, detail="WiFi 操作中，請稍後再試")

        ssid = body.ssid.strip()
        password = body.password

        if not ssid:
            raise HTTPException(400, detail="ssid 不可為空")
        # Open networks have no password; secured networks require ≥ 8 chars
        if password and len(password) < 8:
            raise HTTPException(400, detail="WiFi 密碼至少需要 8 個字元")

        try:
            async with _nmcli_lock:
                success, message = await asyncio.to_thread(
                    _connect_wifi_sync, ssid, password
                )
        except Exception as exc:
            logger.error("WiFi connect error: %s", exc)
            raise HTTPException(500, detail=f"連線失敗：{exc}")

        if not success:
            raise HTTPException(400, detail=message)

        # Remove AP status file → wifi_monitor will detect mode change on next poll
        try:
            if os.path.exists(_AP_STATUS_FILE):
                os.unlink(_AP_STATUS_FILE)
        except OSError as exc:
            logger.warning("Failed to remove AP status file: %s", exc)

        return JSONResponse({"ok": True, "message": f"已連線到「{ssid}」"})

    return router


def _parse_nmcli_scan(output: str) -> list[dict]:
    """Parse `nmcli -t -f SSID,SIGNAL,SECURITY` output into a sorted network list."""
    import re
    _split = re.compile(r"(?<!\\):")
    networks: list[dict] = []
    seen: set[str] = set()
    for line in output.strip().splitlines():
        parts = _split.split(line, maxsplit=2)
        if len(parts) < 3:
            continue
        ssid = parts[0].replace("\\:", ":").strip()
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        try:
            signal = int(parts[1])
        except ValueError:
            signal = 0
        security = parts[2].strip() or "Open"
        networks.append({"ssid": ssid, "signal": signal, "security": security})
    networks.sort(key=lambda n: n["signal"], reverse=True)
    return networks


def _scan_wifi_sync() -> list[dict]:
    """Synchronous WiFi scan via nmcli (requires sudo NOPASSWD for pi user).

    Pi Zero 2W has a single-radio chip; when wlan0 is in AP/hotspot mode,
    forcing a live scan causes nmcli to fail.  wifi_manager.sh pre-scans before
    starting the hotspot and writes results to _WIFI_SCAN_CACHE_FILE — we read
    that first.  Live scan is the fallback for client mode or missing cache.
    """
    # AP mode: use pre-scan cache written by wifi_manager.sh before hotspot started.
    # Single radio (CYW43438) cannot scan while hotspot is active.
    in_ap_mode = os.path.exists(_AP_STATUS_FILE)
    if os.path.exists(_WIFI_SCAN_CACHE_FILE):
        try:
            with open(_WIFI_SCAN_CACHE_FILE, "r", encoding="utf-8") as f:
                networks = _parse_nmcli_scan(f.read())
            if networks:
                return networks
        except OSError:
            pass
    if in_ap_mode:
        return []  # live scan impossible; hotspot occupies the radio

    # Fallback: live scan (client mode only)
    def _run_scan(rescan: str) -> str:
        return subprocess.check_output(
            ["sudo", "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
             "dev", "wifi", "list", "--rescan", rescan],
            text=True, stderr=subprocess.DEVNULL, timeout=20,
        )

    try:
        out = _run_scan("no")
        if not out.strip():
            out = _run_scan("auto")
    except FileNotFoundError:
        return []
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"nmcli exited {exc.returncode}") from exc

    return _parse_nmcli_scan(out)


_SETUP_CON_ID = "EpaperWifiSetup"


def _connect_wifi_sync(ssid: str, password: str) -> tuple[bool, str]:
    """Synchronous WiFi connect via nmcli connection add + up.

    Uses explicit security parameters so nmcli does not need to scan the target
    network — required because wlan0 is occupied by the AP hotspot at this point.
    password may be empty for open (unencrypted) networks.
    """
    try:
        # Remove any leftover profile from a previous setup attempt
        subprocess.run(
            ["sudo", "nmcli", "connection", "delete", _SETUP_CON_ID],
            text=True, capture_output=True, timeout=10,
        )  # ignore return code — profile may not exist

        # Build add command with explicit security settings
        add_cmd = [
            "sudo", "nmcli", "connection", "add",
            "type", "wifi",
            "connection.id", _SETUP_CON_ID,
            "ssid", ssid,
        ]
        if password:
            add_cmd += [
                "wifi-sec.key-mgmt", "wpa-psk",
                "wifi-sec.psk", password,
            ]

        result = subprocess.run(add_cmd, text=True, capture_output=True, timeout=15)
        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()
            return False, f"連線失敗：{err}"

        # Bring the connection up — this also terminates the AP hotspot
        result = subprocess.run(
            ["sudo", "nmcli", "connection", "up", _SETUP_CON_ID],
            text=True, capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            return True, "連線成功"
        err = (result.stderr or result.stdout).strip()
        return False, f"連線失敗：{err}"

    except FileNotFoundError:
        return False, "nmcli 不可用（非 Pi 環境）"
    except subprocess.TimeoutExpired:
        return False, "連線逾時（30 秒）"
