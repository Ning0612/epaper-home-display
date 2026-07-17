from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.state import state
from app.storage.logs import log_env
from app.timezone import configured_now

logger = logging.getLogger(__name__)


async def _sensor_loop(dht22, light, executor: ThreadPoolExecutor, settings) -> None:
    loop = asyncio.get_event_loop()
    while True:
        try:
            try:
                temp, hum = await loop.run_in_executor(executor, dht22.read)
                state.temperature = temp
                state.humidity = hum
            except Exception as exc:
                logger.warning("DHT22 error: %s", exc)

            try:
                raw = await loop.run_in_executor(executor, light.read_raw)
                now = configured_now(settings.timezone)
                previous_raw = state.light_raw
                previous_threshold_exceeded = state.light_is_bright
                threshold_exceeded = raw >= settings.sensors.light.bright_threshold
                state.light_raw = raw
                state.light_is_bright = threshold_exceeded
                if previous_raw is None or threshold_exceeded != previous_threshold_exceeded:
                    state.light_state_since = now
            except Exception as exc:
                state.light_raw = None
                state.light_is_bright = False
                state.light_state_since = None
                logger.warning("Light sensor error: %s", exc)

            await log_env(state.temperature, state.humidity, state.light_raw, state.light_is_bright)
        except Exception as exc:
            logger.error("Sensor loop unexpected error: %s", exc)
        await asyncio.sleep(30)
