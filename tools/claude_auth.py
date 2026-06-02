"""
Claude credentials 設定工具 — 在筆電（有 Claude Code 的機器）執行一次。

優先快速路徑：直接從 Claude Code 的本機 credentials 提取，無需 OAuth 瀏覽器流程。
若找不到 Claude Code credentials，才走 OAuth 授權流程。

執行後會產生 data/claude_creds.json，再 scp 到 Pi：
    scp data/claude_creds.json pi@epaper-display.local:~/epaper-home-display/data/
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import stat
import urllib.parse
import urllib.request
import webbrowser

_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_REDIRECT_URI = "http://localhost:18924/callback"
_SCOPES = "user:inference user:profile"
_CREDS_PATH = os.path.join("data", "claude_creds.json")
_CLAUDE_CODE_CREDS = os.path.expanduser(os.path.join("~", ".claude", ".credentials.json"))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


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
    """快速路徑：從 Claude Code 本機 credentials 提取 token。"""
    if not os.path.exists(_CLAUDE_CODE_CREDS):
        return False
    try:
        with open(_CLAUDE_CODE_CREDS, "r", encoding="utf-8") as f:
            raw = json.load(f)
        oauth = raw.get("claudeAiOauth", {})
        access_token = oauth.get("accessToken") or oauth.get("access_token")
        refresh_token = oauth.get("refreshToken") or oauth.get("refresh_token")
        if not access_token or not refresh_token:
            print("Claude Code credentials 存在但缺少 token，改走 OAuth 流程。")
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


# ── OAuth 手動授權流程（備用）─────────────────────────────────────────────


def _make_pkce() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(96))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def _build_auth_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "scope": urllib.parse.quote(_SCOPES, safe=":"),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return _AUTHORIZE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())


def _exchange_code(code: str, code_verifier: str, state: str) -> dict:
    payload = json.dumps({
        "grant_type": "authorization_code",
        "client_id": _CLIENT_ID,
        "code": code,
        "redirect_uri": _REDIRECT_URI,
        "code_verifier": code_verifier,
        "state": state,
    }).encode()
    req = urllib.request.Request(
        _TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _oauth_flow() -> None:
    code_verifier, code_challenge = _make_pkce()
    oauth_state = _b64url(secrets.token_bytes(16))
    auth_url = _build_auth_url(oauth_state, code_challenge)

    print("\n" + "=" * 60)
    print("  Claude OAuth 手動授權（備用流程）")
    print("=" * 60)
    print("\n步驟 1：在瀏覽器開啟以下網址並登入 Claude 帳號：\n")
    print(f"  {auth_url}\n")
    webbrowser.open(auth_url)

    print("步驟 2：授權後瀏覽器會跳轉到 localhost:18924（可能顯示連線失敗，這是正常的）")
    print("步驟 3：從瀏覽器網址列複製完整 URL，貼到下方。\n")
    print("  形如：http://localhost:18924/callback?code=xxx&state=yyy\n")
    print("  （若不想授權，直接按 Enter 跳過）")

    callback_url = input("\n貼上完整 callback URL：").strip()
    if not callback_url:
        print("已取消授權。")
        return

    parsed = urllib.parse.urlparse(callback_url)
    qs = dict(urllib.parse.parse_qsl(parsed.query))

    if "error" in qs:
        desc = qs.get("error_description", qs["error"])
        print(f"\n授權失敗：{desc}")
        return

    code = qs.get("code")
    if not code and parsed.fragment:
        fqs = dict(urllib.parse.parse_qsl(parsed.fragment))
        code = fqs.get("code")
    if not code:
        print("\n無法從 URL 中解析 code，請確認貼上的是完整 callback URL。")
        return

    if qs.get("state") != oauth_state:
        print("\nstate 不符合，請重新執行腳本（可能是複製了舊的 URL）。")
        return

    print("\n正在換取 token...")
    try:
        token_data = _exchange_code(code, code_verifier, oauth_state)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"\n換取 token 失敗：HTTP {exc.code}\n{body}")
        return
    except Exception as exc:
        print(f"\n換取 token 失敗：{exc}")
        return

    if "access_token" not in token_data:
        print(f"\n換取 token 失敗：{token_data}")
        return

    _save_creds({
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
    })
    print(f"\n授權成功！credentials 已存至 {_CREDS_PATH}")
    _print_scp_hint()


def _print_scp_hint() -> None:
    print("\n請將 credentials 複製到 Pi：")
    print(f"  scp {_CREDS_PATH} pi@epaper-display.local:~/epaper-home-display/data/")
    print("\n完成後 Pi 會在下次 git push 後自動開始收集 Claude 用量。\n")


def main() -> None:
    print("\n=== Claude Credentials 設定 ===")

    if os.path.exists(_CLAUDE_CODE_CREDS):
        print(f"找到 Claude Code credentials：{_CLAUDE_CODE_CREDS}")
        if _extract_from_claude_code():
            print(f"已提取至 {_CREDS_PATH}")
            _print_scp_hint()
            return
    else:
        print(f"未找到 Claude Code credentials（{_CLAUDE_CODE_CREDS}），改走 OAuth 流程。")

    _oauth_flow()


if __name__ == "__main__":
    main()
