from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.config import _AP_STATUS_FILE
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


def _scan_wifi_sync() -> list[dict]:
    """Synchronous WiFi scan via nmcli (requires sudo NOPASSWD for pi user)."""
    import re
    try:
        out = subprocess.check_output(
            [
                "sudo", "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
                "dev", "wifi", "list", "ifname", "wlan0", "--rescan", "yes",
            ],
            text=True, stderr=subprocess.DEVNULL, timeout=20,
        )
    except FileNotFoundError:
        # nmcli not available (non-Pi environment)
        return []
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"nmcli exited {exc.returncode}") from exc

    # nmcli -t escapes literal colons in values as \:
    # Split on unescaped colons using a negative lookbehind
    _split = re.compile(r"(?<!\\):")

    networks: list[dict] = []
    seen: set[str] = set()
    for line in out.strip().splitlines():
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


def _connect_wifi_sync(ssid: str, password: str) -> tuple[bool, str]:
    """Synchronous WiFi connect via nmcli (requires sudo NOPASSWD for pi user).

    password may be empty for open (unencrypted) networks.
    """
    cmd = ["sudo", "nmcli", "dev", "wifi", "connect", ssid, "ifname", "wlan0"]
    if password:
        cmd += ["password", password]
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
        if result.returncode == 0:
            return True, "連線成功"
        err = (result.stderr or result.stdout).strip()
        return False, f"連線失敗：{err}"
    except FileNotFoundError:
        return False, "nmcli 不可用（非 Pi 環境）"
    except subprocess.TimeoutExpired:
        return False, "連線逾時（30 秒）"
