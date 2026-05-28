from __future__ import annotations

import asyncio
import logging
import sys
import functools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime, timedelta as _timedelta

from app.config import load_settings
from app.display.epaper import create_epaper
from app.display.renderer import render_dashboard
from app.logic.alarm_decision import compute_alarm_decision
from app.logic.presence import compute_presence
from app.logic.reminder import generate_reminder
from app.sensors.button import create_button
from app.sensors.dht22 import create_dht22
from app.sensors.light_sensor import create_light_sensor
from app.services.discord import DiscordService
from app.services.mqtt_client import MQTTService
from app.services.voice import VoiceService
from app.services.weather import WeatherService
from app.state import state
from app.storage.db import init_db
from app.storage.logs import (
    get_recent_door_events,
    get_recent_face_events,
    log_alarm_decision,
    log_env,
    log_presence,
    log_system_event,
)
from app.webui.server import create_app

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
                state.light_raw = raw
                state.light_is_bright = light.is_bright(settings.sensors.light.bright_threshold)
            except Exception as exc:
                logger.warning("Light sensor error: %s", exc)

            await log_env(state.temperature, state.humidity, state.light_raw, state.light_is_bright)
        except Exception as exc:
            logger.error("Sensor loop unexpected error: %s", exc)
        await asyncio.sleep(30)


async def _presence_loop(settings, display_queue: asyncio.Queue) -> None:
    while True:
        try:
            door_events = await get_recent_door_events(settings.presence.door_window_seconds)
            face_events = await get_recent_face_events(settings.presence.face_window_seconds)

            score, presence = compute_presence(
                light_is_bright=state.light_is_bright,
                recent_door_events=door_events,
                recent_face_events=face_events,
                button_override=False,
                config=settings.presence,
            )
            state.presence = presence
            state.presence_score = score
            await log_presence(score, presence, "periodic")

            state.active_reminder = generate_reminder(
                state.weather_current,
                state.weather_forecast,
                state.temperature,
                state.humidity,
            )

            if state.last_alert:
                decision, reason = compute_alarm_decision(
                    presence, score, state.last_alert, state.last_face_event
                )
                await log_alarm_decision(decision, reason, score)
        except Exception as exc:
            logger.error("Presence loop error: %s", exc)
        await asyncio.sleep(60)


async def _display_loop(
    epaper, executor: ThreadPoolExecutor, display_queue: asyncio.Queue, settings
) -> None:
    # Every 10th update is a full refresh (clears ghosting); the other nine use
    # init_fast() for a faster partial update.
    refresh_count = 0
    loop = asyncio.get_event_loop()

    while True:
        # Align to wall-clock: trigger at :dashboard_trigger_second each minute.
        # Any display_queue event (button, MQTT alert) fires immediately instead.
        now = _DateTime.now()
        target = settings.display.dashboard_trigger_second
        delay = (target - now.second) % 60 or 60  # `or 60` avoids re-triggering immediately
        try:
            await asyncio.wait_for(display_queue.get(), timeout=delay)
        except asyncio.TimeoutError:
            pass  # wall-clock trigger

        if state.display_busy:
            continue

        full_refresh = (refresh_count % 10 == 0)
        state.display_busy = True
        try:
            # Advance clock by display lag so the rendered HH:MM matches the
            # minute that will be visible when the panel finishes updating.
            render_time = _DateTime.now() + _timedelta(seconds=settings.display.display_lag_seconds)
            image = render_dashboard(state, settings, render_time)
            await loop.run_in_executor(
                executor, functools.partial(epaper.display, image, full_refresh)
            )
            refresh_count += 1  # only advance cadence on successful panel write
        except Exception as exc:
            logger.error("Display update failed: %s", exc)
        finally:
            state.display_busy = False


async def _weather_loop(weather_service: WeatherService, settings) -> None:
    from datetime import datetime
    while True:
        try:
            current, forecast = await weather_service.fetch()
            state.weather_current = current
            state.weather_forecast = forecast
            state.weather_fetched_at = datetime.now()
        except Exception as exc:
            logger.warning("Weather fetch failed (using cached data): %s", exc)
        await asyncio.sleep(settings.weather.fetch_interval_seconds)


async def _handle_button(display_queue: asyncio.Queue) -> None:
    state.presence = "OCCUPIED"
    try:
        display_queue.put_nowait("dashboard")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button press, will render on next cycle")
    logger.info("Button: forced OCCUPIED")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)-26s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    settings = load_settings()
    logger.info("ePaper Home Display starting (tz=%s mock=%s)", settings.timezone, settings.sensors.dht22.use_mock)

    await init_db(settings.storage.db_path)
    await log_system_event("INFO", "main", "ePaper Home Display starting")

    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="hw")
    display_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    dht22 = create_dht22(settings.sensors.dht22)
    light = create_light_sensor(settings.sensors.light)
    button = create_button(settings.sensors.button)
    epaper = create_epaper(settings.display)
    weather_service = WeatherService(settings.weather)
    voice_service = VoiceService(settings.voice)
    discord_service = DiscordService(settings.discord)

    loop = asyncio.get_event_loop()
    mqtt_service = MQTTService(settings.mqtt, display_queue)
    mqtt_service.start(loop)

    from app.services.mqtt_client import make_done_callback

    def _on_button():
        future = asyncio.run_coroutine_threadsafe(_handle_button(display_queue), loop)
        future.add_done_callback(make_done_callback("Button callback"))

    button.register_callback(_on_button)

    import uvicorn
    uvicorn_config = uvicorn.Config(
        create_app(settings, weather_service),
        host=settings.webui.host,
        port=settings.webui.port,
        log_level="warning",
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("WebUI → http://%s:%d", settings.webui.host, settings.webui.port)

    try:
        await asyncio.gather(
            _sensor_loop(dht22, light, executor, settings),
            _presence_loop(settings, display_queue),
            _display_loop(epaper, executor, display_queue, settings),
            _weather_loop(weather_service, settings),
            server.serve(),
        )
    finally:
        mqtt_service.stop()
        executor.shutdown(wait=False)
        await log_system_event("INFO", "main", "ePaper Home Display stopped")


if __name__ == "__main__":
    asyncio.run(main())
