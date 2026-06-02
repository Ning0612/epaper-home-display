"""
Claude credentials 設定工具 — 在筆電（有 Claude Code 的機器）執行一次。

從 Claude Code 的本機 credentials 提取 token。
若找不到 Claude Code credentials，請先安裝 Claude Code 並登入後再執行。

執行後會產生 data/claude_creds.json，再 scp 到 Pi：
    scp data/claude_creds.json pi@epaper-display.local:~/epaper-home-display/data/
"""
from __future__ import annotations

import json
import os
import stat

_CREDS_PATH = os.path.join("data", "claude_creds.json")
_CLAUDE_CODE_CREDS = os.path.expanduser(os.path.join("~", ".claude", ".credentials.json"))


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


def _extract_from_claude_code() -> bool:
    """從 Claude Code 本機 credentials 提取 token。"""
    if not os.path.exists(_CLAUDE_CODE_CREDS):
        return False
    try:
        with open(_CLAUDE_CODE_CREDS, "r", encoding="utf-8") as f:
            raw = json.load(f)
        oauth = raw.get("claudeAiOauth", {})
        access_token = oauth.get("accessToken") or oauth.get("access_token")
        refresh_token = oauth.get("refreshToken") or oauth.get("refresh_token")
        if not access_token or not refresh_token:
            return False
        creds = {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
        _save_creds(creds)
        return True
    except Exception as exc:
        print(f"讀取 Claude Code credentials 失敗：{exc}")
        return False


def _print_scp_hint() -> None:
    print("\n請將 credentials 複製到 Pi：")
    print(f"  scp {_CREDS_PATH} pi@epaper-display.local:~/epaper-home-display/data/")
    print("\n完成後 Pi 會在下次 git push 後自動開始收集 Claude 用量。\n")


def main() -> None:
    print("\n=== Claude Credentials 設定 ===\n")

    if not os.path.exists(_CLAUDE_CODE_CREDS):
        print(f"找不到 Claude Code credentials：{_CLAUDE_CODE_CREDS}")
        print("請先自行安裝 Claude Code 並完成登入，再重新執行本腳本：")
        print("  python tools/claude_auth.py")
        return

    print(f"找到 Claude Code credentials：{_CLAUDE_CODE_CREDS}")

    if _extract_from_claude_code():
        print(f"已提取至 {_CREDS_PATH}")
        _print_scp_hint()
    else:
        print("credentials 格式無效，請確認 Claude Code 已正常登入，再重新執行本腳本：")
        print("  python tools/claude_auth.py")


if __name__ == "__main__":
    main()
