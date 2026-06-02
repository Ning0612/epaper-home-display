from __future__ import annotations

import json
import logging
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

_USAGE_HEADERS = {
    "anthropic-beta": "oauth-2025-04-20",
    "User-Agent": "claude-code/2.0.32",
    "Accept": "application/json",
}


@dataclass
class ClaudeUsageData:
    usage_5h: float
    usage_7d: float
    reset_5h: str
    reset_7d: str


class _UnauthorizedError(Exception):
    pass


class _RateLimitedError(Exception):
    pass


def _fmt_reset_time(iso: str) -> str:
    """Convert ISO timestamp to local HH:MM string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%H:%M")
    except Exception:
        return "--:--"


def _fmt_remaining(iso: str) -> str:
    """Convert ISO timestamp to 'Xd Xh' remaining string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = dt - now
        if diff.total_seconds() <= 0:
            return "0h"
        days = diff.days
        hours = diff.seconds // 3600
        if days > 0:
            return f"{days}d {hours}h"
        return f"{hours}h"
    except Exception:
        return "--:--"


class ClaudeUsageService:
    def __init__(self, creds_path: str) -> None:
        self._creds_path = creds_path
        self._creds: dict | None = None

    def load_credentials(self) -> bool:
        if not os.path.exists(self._creds_path):
            return False
        try:
            with open(self._creds_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Support Claude Code's nested format: {"claudeAiOauth": {...}}
            if "claudeAiOauth" in raw:
                raw = raw["claudeAiOauth"]
            # Normalize camelCase (Claude Code) → snake_case (our internal format)
            access_token = raw.get("access_token") or raw.get("accessToken")
            refresh_token = raw.get("refresh_token") or raw.get("refreshToken")
            if not access_token or not refresh_token:
                return False
            self._creds = {"access_token": access_token, "refresh_token": refresh_token}
            return True
        except Exception as exc:
            logger.warning("Failed to load claude_creds.json: %s", exc)
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
            logger.warning("Failed to save claude_creds.json: %s", exc)

    async def _refresh_token(self, session: aiohttp.ClientSession) -> bool:
        if not self._creds or not self._creds.get("refresh_token"):
            return False
        try:
            async with session.post(
                _TOKEN_URL,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self._creds["refresh_token"],
                    "client_id": _CLIENT_ID,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("Token refresh failed: HTTP %s", resp.status)
                    return False
                data = await resp.json()
                self._creds["access_token"] = data["access_token"]
                if "refresh_token" in data:
                    self._creds["refresh_token"] = data["refresh_token"]
                self._save_credentials()
                logger.info("Claude OAuth token refreshed")
                return True
        except Exception as exc:
            logger.warning("Token refresh error: %s", exc)
            return False

    async def fetch_usage(self) -> ClaudeUsageData | None:
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
                        logger.warning("Claude usage: still 401 after token refresh")
                        return None
                return None

    async def _do_fetch(self, session: aiohttp.ClientSession) -> ClaudeUsageData | None:
        headers = dict(_USAGE_HEADERS)
        headers["Authorization"] = f"Bearer {self._creds['access_token']}"
        try:
            async with session.get(
                _USAGE_URL,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    raise _UnauthorizedError()
                if resp.status == 429:
                    logger.warning("Claude usage API rate limited (429) — keeping cached data")
                    raise _RateLimitedError()
                if resp.status != 200:
                    logger.warning("Claude usage API returned HTTP %s", resp.status)
                    return None
                body = await resp.json()
                return _parse_usage(body)
        except (_UnauthorizedError, _RateLimitedError):
            raise
        except aiohttp.ClientError as exc:
            logger.warning("Claude usage API request error: %s", exc)
            return None
        except Exception as exc:
            logger.warning("Claude usage API unexpected error: %s", exc)
            return None


def _parse_usage(body: dict) -> ClaudeUsageData | None:
    try:
        fh = body["five_hour"]
        sd = body.get("seven_day")  # null for some subscription tiers
        return ClaudeUsageData(
            usage_5h=fh["utilization"] / 100.0,
            usage_7d=(sd["utilization"] / 100.0) if sd and sd.get("utilization") is not None else 0.0,
            reset_5h=_fmt_reset_time(fh["resets_at"]),
            reset_7d=_fmt_remaining(sd["resets_at"]) if sd else "--:--",
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Unexpected Claude usage API response format: %s", exc)
        return None
