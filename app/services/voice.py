from __future__ import annotations

import asyncio
import logging
import os

from app.config import VoiceConfig

logger = logging.getLogger(__name__)

_ALLOWED_PLAYERS = frozenset({"aplay", "mpg123", "mpg321", "omxplayer", "paplay", "cvlc"})


class VoiceService:
    def __init__(self, config: VoiceConfig) -> None:
        player = os.path.basename((config.player or "").strip())
        if player not in _ALLOWED_PLAYERS:
            logger.warning("voice.player %r not in allowlist; falling back to aplay", config.player)
            player = "aplay"
        config.player = player
        self._config = config

    async def play(self, filename: str) -> None:
        if not self._config.enabled:
            return
        safe_name = os.path.basename(filename)
        if not safe_name:
            logger.warning("play() called with empty or directory-only filename: %r", filename)
            return
        sounds_real = os.path.realpath(self._config.sounds_dir)
        path = os.path.realpath(os.path.join(self._config.sounds_dir, safe_name))
        if not path.startswith(sounds_real + os.sep) and path != sounds_real:
            logger.warning("Refusing to play file outside sounds dir: %s", filename)
            return
        if not os.path.isfile(path):
            logger.warning("Sound file not found: %s", path)
            return
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self._config.player, path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            logger.info("Played: %s", filename)
        except asyncio.CancelledError:
            if proc is not None and proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    try:
                        await proc.wait()
                    except Exception:
                        pass
                except Exception:
                    pass
            raise
        except Exception as exc:
            logger.warning("Voice play failed: %s", exc)
