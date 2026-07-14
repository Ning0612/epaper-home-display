from __future__ import annotations

import logging
import json
from typing import TypeAlias

import aiohttp

from app.config import DiscordConfig

logger = logging.getLogger(__name__)

DiscordMessage: TypeAlias = str | dict


def serialize_message(message: DiscordMessage) -> str:
    """Store text or an embed payload in the existing notification queue column."""
    if isinstance(message, str):
        return message
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


def deserialize_message(stored: str) -> DiscordMessage:
    """Decode queued embed JSON while keeping legacy plain-text rows readable."""
    if not stored.lstrip().startswith("{"):
        return stored
    try:
        payload = json.loads(stored)
    except json.JSONDecodeError:
        return stored
    return payload if isinstance(payload, dict) and "embeds" in payload else stored


class DiscordService:
    def __init__(self, config: DiscordConfig) -> None:
        self._config = config

    async def send(self, message: DiscordMessage) -> bool:
        if not self._config.webhook_url:
            logger.debug("Discord webhook not configured")
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._config.webhook_url,
                    json=message if isinstance(message, dict) else {"content": message},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    ok = resp.status in (200, 204)
                    if not ok:
                        logger.warning("Discord returned HTTP %d", resp.status)
                    return ok
        except Exception as exc:
            logger.warning("Discord send failed: %s", exc)
            return False
