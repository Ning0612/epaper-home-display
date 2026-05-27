from __future__ import annotations

import asyncio
import logging
import os

from app.config import VoiceConfig

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self, config: VoiceConfig) -> None:
        self._config = config

    async def play(self, filename: str) -> None:
        if not self._config.enabled:
            return
        path = os.path.join(self._config.sounds_dir, filename)
        if not os.path.exists(path):
            logger.warning("Sound file not found: %s", path)
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                self._config.player, path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            logger.info("Played: %s", filename)
        except Exception as exc:
            logger.warning("Voice play failed: %s", exc)
