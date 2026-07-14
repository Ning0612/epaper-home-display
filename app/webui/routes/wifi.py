from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.requests import Request

from app.config import _AP_STATUS_FILE, _WIFI_SCAN_CACHE_FILE
from app.state import state
from app.webui.routes.auth import _preauth_csrf_token
from app.webui.templates.wifi import _render_wifi

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
    async def wifi_page(request: Request):
        """AP mode WiFi setup portal; first-run is public, configured devices require login."""
        return HTMLResponse(_render_wifi(getattr(request.state, "csrf_token", _preauth_csrf_token())))

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
            raise HTTPException(500, detail="WiFi 掃描失敗，請稍後再試") from exc

    @router.post("/api/wifi/connect")
    async def wifi_connect(body: _WifiConnectBody, background_tasks: BackgroundTasks):
        """Connect to a WiFi network.

        Phase 1 (synchronous, before response): create NM connection profile.
        AP hotspot stays up so the HTTP 200 response reaches the client.

        Phase 2 (BackgroundTask, after response): activate profile.
        AP shuts down here.  AP status file is removed only on success so the
        portal remains available for retry if activation fails.
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
        if "\n" in password or "\r" in password:
            raise HTTPException(400, detail="WiFi 密碼不可包含換行")

        # Phase 1: build NM profile (AP stays up, client receives this response)
        try:
            async with _nmcli_lock:
                ok, msg = await asyncio.to_thread(_prepare_wifi_profile_sync, ssid, password)
        except Exception as exc:
            logger.error("WiFi prepare error: %s", exc)
            raise HTTPException(500, detail="WiFi 設定失敗，請稍後再試") from exc

        if not ok:
            raise HTTPException(400, detail=msg)

        # Phase 2: activate after client receives 200 (AP will shut down)
        background_tasks.add_task(_activate_wifi_background, ssid, password)

        return JSONResponse({"ok": True, "message": "正在切換網路，AP 熱點即將關閉..."})

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


def _prepare_wifi_profile_sync(ssid: str, password: str) -> tuple[bool, str]:
    """Phase 1: delete stale profile + create new NM connection profile.

    Does NOT activate the connection — the AP hotspot stays up so the HTTP
    response can reach the client before the network is switched.
    """
    try:
        subprocess.run(
            ["sudo", "nmcli", "connection", "delete", _SETUP_CON_ID],
            text=True, capture_output=True, timeout=10,
        )  # ignore return code — profile may not exist

        add_cmd = [
            "sudo", "nmcli", "connection", "add",
            "type", "wifi",
            "connection.id", _SETUP_CON_ID,
            "ssid", ssid,
        ]
        if password:
            # Leave the secret unset during phase 1.  Phase 2 supplies it to
            # nmcli through stdin so it never appears in process argv.
            add_cmd += ["wifi-sec.key-mgmt", "wpa-psk"]

        result = subprocess.run(add_cmd, text=True, capture_output=True, timeout=15)
        if result.returncode != 0:
            logger.warning(
                "WiFi profile creation failed for %r: %s",
                ssid,
                (result.stderr or result.stdout).strip(),
            )
            return False, "建立連線設定失敗，請確認 SSID 與密碼"
        return True, "profile created"

    except FileNotFoundError:
        return False, "nmcli 不可用（非 Pi 環境）"
    except subprocess.TimeoutExpired:
        return False, "建立連線設定逾時"


def _activate_wifi_profile_sync(password: str = "") -> tuple[bool, str]:
    """Phase 2 sync: bring up the pre-created EpaperWifiSetup connection.

    This terminates the AP hotspot as a side-effect.  For secured networks,
    `--ask` reads the secret from stdin instead of exposing it in argv.
    """
    try:
        command = ["sudo", "nmcli"]
        input_text = None
        if password:
            command.append("--ask")
            input_text = password + "\n"
        command += ["connection", "up", _SETUP_CON_ID]
        result = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, "連線成功"
        return False, "連線失敗，請確認 WiFi 設定"
    except FileNotFoundError:
        return False, "nmcli 不可用（非 Pi 環境）"
    except subprocess.TimeoutExpired:
        return False, "連線逾時（30 秒）"


async def _activate_wifi_background(ssid: str, password: str = "") -> None:
    """Phase 2 BackgroundTask: activate WiFi after HTTP response is sent.

    Sleeps 1s to let ASGI flush the response before the AP shuts down.
    AP status file is removed only on success — if activation fails, the
    portal remains accessible for retry.
    """
    await asyncio.sleep(1.0)
    try:
        async with _nmcli_lock:
            ok, msg = await asyncio.to_thread(_activate_wifi_profile_sync, password)
        if ok:
            try:
                if os.path.exists(_AP_STATUS_FILE):
                    os.unlink(_AP_STATUS_FILE)
            except OSError as exc:
                logger.warning("Failed to remove AP status file: %s", exc)
            logger.info("WiFi activated: connected to %s", ssid)
        else:
            logger.error("WiFi activation failed for %s: %s", ssid, msg)
            # AP status file intentionally kept — portal remains for retry
    except Exception:
        logger.exception("Background WiFi activation error for %s", ssid)
        # AP status file intentionally kept — portal remains for retry
