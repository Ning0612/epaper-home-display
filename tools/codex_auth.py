"""
Codex credentials 設定工具 — 在筆電（有 Codex CLI 的機器）執行一次。

從 Codex CLI 的本機 credentials 提取 OAuth tokens，
存為 data/codex_creds.json，再 scp 到 Pi。

    python tools/codex_auth.py
    scp data/codex_creds.json pi@epaper-display.local:~/epaper-home-display/data/
"""
from __future__ import annotations

import base64
import json
import os
import stat

_CODEX_AUTH = os.path.expanduser(os.path.join("~", ".codex", "auth.json"))
_CREDS_PATH = os.path.join("data", "codex_creds.json")


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        b64 = parts[1]
        b64 += "=" * ((-len(b64)) % 4)
        return json.loads(base64.urlsafe_b64decode(b64).decode("utf-8"))
    except Exception:
        return {}


def _save_creds(creds: dict) -> None:
    os.makedirs("data", exist_ok=True)
    tmp_path = _CREDS_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)
    os.replace(tmp_path, _CREDS_PATH)
    try:
        os.chmod(_CREDS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def main() -> None:
    print("\n=== Codex Credentials 設定 ===\n")

    if not os.path.exists(_CODEX_AUTH):
        print(f"找不到 Codex auth 檔案：{_CODEX_AUTH}")
        print("請先安裝 Codex CLI 並登入（codex login），再執行此腳本。")
        return

    print(f"找到 Codex credentials：{_CODEX_AUTH}")

    try:
        with open(_CODEX_AUTH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as exc:
        print(f"讀取失敗：{exc}")
        return

    auth_mode = raw.get("auth_mode", "")
    tokens = raw.get("tokens", {})

    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    id_token = tokens.get("id_token", "")
    # account_id is nested inside tokens
    account_id = tokens.get("account_id", "") or raw.get("account_id", "")

    if not access_token or not account_id:
        print("auth.json 中缺少 access_token 或 account_id，請重新登入 Codex CLI。")
        return

    if not refresh_token:
        print("警告：找不到 refresh_token，access_token 過期後需手動重新執行此腳本（約 1 小時後）。")

    # Try to extract client_id from id_token JWT for future token refresh
    client_id = ""
    if id_token:
        payload = _decode_jwt_payload(id_token)
        aud = payload.get("aud")
        if isinstance(aud, str) and not aud.startswith("http"):
            client_id = aud
        elif isinstance(aud, list):
            for a in aud:
                if isinstance(a, str) and not a.startswith("http"):
                    client_id = a
                    break

    creds: dict = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "account_id": account_id,
        "auth_mode": auth_mode,
    }
    if client_id:
        creds["client_id"] = client_id

    _save_creds(creds)
    print(f"已提取至 {_CREDS_PATH}")
    if client_id:
        print(f"  client_id（從 id_token 解析）：{client_id}")

    print("\n請將 credentials 複製到 Pi：")
    print(f"  scp {_CREDS_PATH} pi@epaper-display.local:~/epaper-home-display/data/")
    print("\n注意：access_token 約 1 小時後過期。")
    print("      若 Pi log 出現 401 錯誤，請重新執行此腳本並重新 scp。\n")


if __name__ == "__main__":
    main()
