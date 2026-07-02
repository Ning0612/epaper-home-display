"""
Interactive Bambu Lab cloud credentials setup.

Run this once on a laptop, then copy data/bambu_creds.json to the Pi:
    scp data/bambu_creds.json pi@epaper-display.local:~/epaper-home-display/data/
"""
from __future__ import annotations

import asyncio
import getpass
import json
import os
import stat
from typing import Any

import aiohttp

_LOGIN_URL = "https://api.bambulab.com/v1/user-service/user/login"
_PREFERENCE_URL = "https://api.bambulab.com/v1/design-user-service/my/preference"
_BIND_URL = "https://api.bambulab.com/v1/iot-service/api/user/bind"
_CREDS_PATH = os.path.join("data", "bambu_creds.json")


class BambuAuthError(Exception):
    pass


async def _request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, str] | None = None,
) -> Any:
    try:
        async with session.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            text = await resp.text()
            if resp.status < 200 or resp.status >= 300:
                detail = text.strip()
                if len(detail) > 300:
                    detail = detail[:300] + "..."
                raise BambuAuthError(f"HTTP {resp.status}: {detail or 'empty response'}")
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise BambuAuthError(f"API returned invalid JSON: {exc}") from exc
    except aiohttp.ClientError as exc:
        raise BambuAuthError(f"Network request failed: {exc}") from exc
    except asyncio.TimeoutError as exc:
        raise BambuAuthError("Network request timed out") from exc


async def _login(session: aiohttp.ClientSession, account: str, password: str) -> dict:
    body = await _request_json(
        session,
        "POST",
        _LOGIN_URL,
        json_body={"account": account, "password": password},
    )
    if not isinstance(body, dict):
        raise BambuAuthError("Login API returned an unexpected response format")

    if body.get("loginType") == "verifyCode":
        print("\n請至信箱查收驗證碼")
        code = input("驗證碼: ").strip()
        if not code:
            raise BambuAuthError("Verification code cannot be empty")
        body = await _request_json(
            session,
            "POST",
            _LOGIN_URL,
            json_body={"account": account, "code": code},
        )
        if not isinstance(body, dict):
            raise BambuAuthError("Verification login API returned an unexpected response format")

    access_token = body.get("accessToken")
    if not isinstance(access_token, str) or not access_token:
        raise BambuAuthError("Login did not return accessToken; please check account, password, or verification code")
    return body


async def _get_uid(session: aiohttp.ClientSession, access_token: str) -> str:
    body = await _request_json(
        session,
        "GET",
        _PREFERENCE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not isinstance(body, dict):
        raise BambuAuthError("Preference API returned an unexpected response format")
    uid = body.get("uid")
    # The API returns uid as a JSON number (e.g. 1234567890), not a string.
    if isinstance(uid, bool):
        uid = None
    elif isinstance(uid, int):
        uid = str(uid)
    elif isinstance(uid, str):
        uid = uid.strip() or None
    else:
        uid = None
    if not uid:
        raise BambuAuthError("Preference API response did not include uid")
    return uid


async def _get_devices(session: aiohttp.ClientSession, access_token: str) -> list[dict]:
    body = await _request_json(
        session,
        "GET",
        _BIND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    # The API wraps the device list in an object: {"message":"success","devices":[...]}.
    # Some older/alternate responses may return the array directly, so accept both.
    if isinstance(body, dict):
        devices = body.get("devices")
    elif isinstance(body, list):
        devices = body
    else:
        devices = None
    if not isinstance(devices, list):
        raise BambuAuthError("Device list API returned an unexpected response format")
    return [item for item in devices if isinstance(item, dict)]


def _choose_serial(devices: list[dict]) -> str:
    valid_devices = [device for device in devices if isinstance(device.get("dev_id"), str) and device["dev_id"]]
    if devices and not valid_devices:
        print(
            "\n裝置清單格式與預期不符（回傳項目缺少 dev_id 欄位，Bambu API 格式可能已變更），"
            "請手動輸入印表機序號。"
        )
    if len(valid_devices) == 1:
        serial = valid_devices[0]["dev_id"]
        name = valid_devices[0].get("name") or valid_devices[0].get("dev_model_name") or "Bambu printer"
        print(f"\n找到 1 台裝置，自動採用: {name} ({serial})")
        return serial

    if len(valid_devices) > 1:
        print("\n找到多台裝置，請選擇要使用的印表機:")
        for idx, device in enumerate(valid_devices, start=1):
            name = device.get("name") or "(no name)"
            model = device.get("dev_model_name") or "(unknown model)"
            print(f"  {idx}. {name} / {model} / {device['dev_id']}")
        while True:
            choice = input(f"請輸入 1-{len(valid_devices)}: ").strip()
            try:
                index = int(choice)
            except ValueError:
                print("請輸入數字。")
                continue
            if 1 <= index <= len(valid_devices):
                return valid_devices[index - 1]["dev_id"]
            print("選項超出範圍。")

    if not devices:
        print("\n無法從 Bambu API 取得裝置清單，請手動輸入印表機序號。")
    while True:
        serial = input("印表機序號 serial: ").strip()
        if serial:
            return serial
        print("序號不能空白。")


def _save_creds(creds: dict) -> None:
    try:
        os.makedirs("data", exist_ok=True)
        tmp_path = _CREDS_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
        os.replace(tmp_path, _CREDS_PATH)
    except OSError as exc:
        raise BambuAuthError(f"Failed to write {_CREDS_PATH}: {exc}") from exc
    try:
        os.chmod(_CREDS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _print_scp_hint() -> None:
    print("\n請將 credentials 複製到 Pi:")
    print(f"  scp {_CREDS_PATH} pi@epaper-display.local:~/epaper-home-display/data/")
    print("\n若 MQTT 日後回報認證失敗，請重新執行本工具並再次複製 credentials。")


async def _run() -> None:
    print("\n=== Bambu Lab Cloud Credentials Setup ===\n")
    account = input("Bambu Lab email: ").strip()
    if not account:
        raise BambuAuthError("Email cannot be empty")
    password = getpass.getpass("Bambu Lab password: ")
    if not password:
        raise BambuAuthError("Password cannot be empty")

    async with aiohttp.ClientSession() as session:
        login_body = await _login(session, account, password)
        access_token = login_body["accessToken"]
        uid = await _get_uid(session, access_token)

        devices: list[dict] = []
        try:
            devices = await _get_devices(session, access_token)
        except BambuAuthError as exc:
            print(f"\n取得裝置清單失敗，改為手動輸入序號: {exc}")
        serial = _choose_serial(devices)

    _save_creds(
        {
            "access_token": access_token,
            "uid": uid,
            "serial": serial,
        }
    )
    print(f"\n已儲存 {_CREDS_PATH}")
    _print_scp_hint()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n已取消。")
    except BambuAuthError as exc:
        print(f"\n錯誤: {exc}")
    except Exception as exc:
        print(f"\n未預期錯誤: {exc}")


if __name__ == "__main__":
    main()
