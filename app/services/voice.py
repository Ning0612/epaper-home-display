from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid

from app.config import VoiceConfig

logger = logging.getLogger(__name__)

_ALLOWED_PLAYERS = frozenset({"aplay", "mpg123", "mpg321", "omxplayer", "paplay", "cvlc"})
_ALLOWED_TTS_ENGINES = frozenset({"espeak-ng", "none"})
_ALSA_CONTROL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$")


class VoiceService:
    def __init__(self, config: VoiceConfig) -> None:
        player = os.path.basename((config.player or "").strip())
        if player not in _ALLOWED_PLAYERS:
            logger.warning("voice.player %r not in allowlist; falling back to aplay", config.player)
            player = "aplay"
        config.player = player
        tts_engine = (config.tts_engine or "none").strip()
        if tts_engine not in _ALLOWED_TTS_ENGINES:
            logger.warning("voice.tts_engine %r not in allowlist; disabling TTS", config.tts_engine)
            tts_engine = "none"
        config.tts_engine = tts_engine
        config.volume = max(0, min(100, int(config.volume)))
        ctrl = (config.alsa_mixer_control or "").strip()
        if ctrl and not _ALSA_CONTROL_RE.match(ctrl):
            logger.warning("voice.alsa_mixer_control %r is invalid; disabling volume control", config.alsa_mixer_control)
            ctrl = ""
        config.alsa_mixer_control = ctrl
        self._config = config

    async def _set_volume(self) -> None:
        """Set ALSA mixer volume (best-effort; failures are non-fatal)."""
        control = (self._config.alsa_mixer_control or "").strip()
        if not control:
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                "amixer", "sset", control, f"{self._config.volume}%",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode != 0:
                logger.debug("amixer exited with code %d for control %r", proc.returncode, control)
        except Exception as exc:
            logger.debug("amixer volume set skipped: %s", exc)

    async def _run_player(self, path: str, label: str) -> None:
        """Invoke the configured audio player on an absolute path."""
        await self._set_volume()
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self._config.player, path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            logger.info("Played: %s", label)
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
            logger.warning("Voice play failed (%s): %s", label, exc)

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
        await self._run_player(path, filename)

    async def speak_or_play(self, text: str, fallback_filename: str) -> None:
        """Use TTS if enabled and successful; fall back to a pre-recorded file otherwise."""
        if self._config.tts_engine != "none":
            if await self.speak(text):
                return
            logger.warning("TTS failed; falling back to %s", fallback_filename)
        await self.play(fallback_filename)

    async def speak(self, text: str) -> bool:
        """Synthesize text with the configured TTS engine and play it.

        Returns True if playback completed, False on any non-cancellation failure.
        CancelledError propagates to the caller unchanged.
        """
        if not self._config.enabled:
            return False
        if self._config.tts_engine == "none":
            return False
        if not text:
            return False
        tmp_dir = "/dev/shm" if os.path.isdir("/dev/shm") else "/tmp"
        tmp_path = os.path.join(tmp_dir, f"tts_{uuid.uuid4().hex[:8]}.wav")
        tts_proc = None
        try:
            tts_proc = await asyncio.create_subprocess_exec(
                "espeak-ng",
                "-v", self._config.tts_language,
                "-s", str(self._config.tts_speed),
                text,
                "-w", tmp_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await tts_proc.wait()
            if tts_proc.returncode != 0:
                logger.warning("espeak-ng exited with code %d for text %r", tts_proc.returncode, text)
                return False
            if not os.path.isfile(tmp_path):
                logger.warning("espeak-ng produced no output file for text %r", text)
                return False
            await self._run_player(tmp_path, "tts")
            return True
        except asyncio.CancelledError:
            if tts_proc is not None and tts_proc.returncode is None:
                tts_proc.terminate()
                try:
                    await asyncio.wait_for(tts_proc.wait(), timeout=2.0)
                except (asyncio.TimeoutError, Exception):
                    pass
            raise
        except Exception as exc:
            logger.warning("TTS speak failed: %s", exc)
            return False
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
