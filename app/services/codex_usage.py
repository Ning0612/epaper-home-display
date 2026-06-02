from __future__ import annotations

import json
import logging
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)

_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
# Auth0 token refresh for ChatGPT-auth mode Codex CLI
_TOKEN_URL = "https://auth.openai.com/oauth/token"


@dataclass
class CodexUsageData:
    usage_5h: float
    usage_7d: float
    reset_5h: str
    reset_7d: str


class _UnauthorizedError(Exception):
    pass


class _RateLimitedError(Exception):
    pass


def _fmt_unix_local(ts: int) -> str:
    """Convert Unix seconds to local HH:MM."""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%H:%M")
    except Exception:
        return "--"


def _fmt_unix_remaining(ts: int) -> str:
    """Convert Unix seconds to 'Xd Xh' remaining."""
    try:
        diff = datetime.fromtimestamp(ts, tz=timezone.utc) - datetime.now(timezone.utc)
        if diff.total_seconds() <= 0:
            return "0h"
        days, hours = diff.days, diff.seconds // 3600
        return f"{days}d {hours}h" if days > 0 else f"{hours}h"
    except Exception:
        return "--"


class CodexUsageService:
    def __init__(self, creds_path: str) -> None:
        self._creds_path = creds_path
        self._creds: dict | None = None

    def load_credentials(self) -> bool:
        if not os.path.exists(self._creds_path):
            return False
        try:
            with open(self._creds_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            access_token = raw.get("access_token")
            refresh_token = raw.get("refresh_token")
            account_id = raw.get("account_id")
            if not access_token or not account_id:
                return False
            self._creds = {
                "access_token": access_token,
                "refresh_token": refresh_token or "",
                "account_id": account_id,
                "client_id": raw.get("client_id", ""),
            }
            return True
        except Exception as exc:
            logger.warning("Failed to load codex_creds.json: %s", exc)
            return False

    def _save_credentials(self) -> None:
        if self._creds is None:
            return
        try:
            os.makedirs(os.path.dirname(self._creds_path) or ".", exist_ok=True)
            tmp_path = self._creds_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._creds, f, indent=2)
            os.replace(tmp_path, self._creds_path)
            try:
                os.chmod(self._creds_path, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass
        except Exception as exc:
            logger.warning("Failed to save codex_creds.json: %s", exc)

    async def _refresh_token(self, session: aiohttp.ClientSession) -> bool:
        if not self._creds or not self._creds.get("refresh_token"):
            return False
        client_id = self._creds.get("client_id", "")
        body: dict = {
            "grant_type": "refresh_token",
            "refresh_token": self._creds["refresh_token"],
        }
        if client_id:
            body["client_id"] = client_id
        try:
            async with session.post(
                _TOKEN_URL,
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Codex token refresh failed: HTTP %s — re-run tools/codex_auth.py on laptop",
                        resp.status,
                    )
                    return False
                data = await resp.json()
                self._creds["access_token"] = data["access_token"]
                if "refresh_token" in data:
                    self._creds["refresh_token"] = data["refresh_token"]
                self._save_credentials()
                logger.info("Codex OAuth token refreshed")
                return True
        except Exception as exc:
            logger.warning("Codex token refresh error: %s", exc)
            return False

    async def fetch_usage(self) -> CodexUsageData | None:
        if not self._creds or not self._creds.get("access_token"):
            return None

        async with aiohttp.ClientSession() as session:
            try:
                return await self._do_fetch(session)
            except _UnauthorizedError:
                if await self._refresh_token(session):
                    try:
                        return await self._do_fetch(session)
                    except _UnauthorizedError:
                        logger.warning(
                            "Codex usage: still 401 after token refresh — "
                            "re-run tools/codex_auth.py on laptop"
                        )
                        return None
                return None

    async def _do_fetch(self, session: aiohttp.ClientSession) -> CodexUsageData | None:
        headers = {
            "Authorization": f"Bearer {self._creds['access_token']}",
            "ChatGPT-Account-Id": self._creds["account_id"],
            "Accept": "application/json",
        }
        try:
            async with session.get(
                _USAGE_URL,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise _UnauthorizedError()
                if resp.status == 429:
                    logger.warning("Codex usage API rate limited (429) — keeping cached data")
                    raise _RateLimitedError()
                if resp.status != 200:
                    logger.warning("Codex usage API returned HTTP %s", resp.status)
                    return None
                body = await resp.json()
                return _parse_usage(body)
        except (_UnauthorizedError, _RateLimitedError):
            raise
        except aiohttp.ClientError as exc:
            logger.warning("Codex usage API request error: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Codex usage API unexpected error: %s", exc)
            return None


def _parse_usage(body: dict) -> CodexUsageData | None:
    try:
        # Two wire formats observed in the wild; resolve each window independently
        rl = body.get("rate_limits") or {}
        rl2 = body.get("rate_limit") or {}
        primary = rl.get("primary") or rl2.get("primary_window") or {}
        secondary = rl.get("secondary") or rl2.get("secondary_window") or {}

        p_pct = primary.get("used_percent")
        s_pct = secondary.get("used_percent")
        p_reset = primary.get("resets_at") or primary.get("reset_at")
        s_reset = secondary.get("resets_at") or secondary.get("reset_at")

        reset_5h = _fmt_unix_local(p_reset) if isinstance(p_reset, (int, float)) else "--"
        reset_7d = _fmt_unix_remaining(s_reset) if isinstance(s_reset, (int, float)) else "--"

        return CodexUsageData(
            usage_5h=(float(p_pct) / 100.0) if p_pct is not None else 0.0,
            usage_7d=(float(s_pct) / 100.0) if s_pct is not None else 0.0,
            reset_5h=reset_5h,
            reset_7d=reset_7d,
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Unexpected Codex usage API response format: %s", exc)
        return None
