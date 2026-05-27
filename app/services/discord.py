from __future__ import annotations

import logging

import aiohttp

from app.config import DiscordConfig

logger = logging.getLogger(__name__)


class DiscordService:
    def __init__(self, config: DiscordConfig) -> None:
        self._webhook_url = config.webhook_url

    async def send(self, message: str) -> bool:
        if not self._webhook_url:
            logger.debug("Discord webhook not configured")
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._webhook_url,
                    json={"content": message},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    ok = resp.status in (200, 204)
                    if not ok:
                        logger.warning("Discord returned HTTP %d", resp.status)
                    return ok
        except Exception as exc:
            logger.warning("Discord send failed: %s", exc)
            return False
