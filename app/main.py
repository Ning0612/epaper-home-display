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
from app.services.notification_manager import NotificationManager
from app.services.voice import VoiceService
from app.services.weather import WeatherService
from app.state import state
from app.storage.db import init_db
from app.storage.logs import (
    end_desk_session,
    get_ongoing_desk_session,
    get_sessions_for_date,
    log_alarm_decision,
    log_env,
    log_presence,
    log_system_event,
    start_desk_session,
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


async def _presence_loop(
    display_queue: asyncio.Queue, mqtt_service, notification_manager: NotificationManager, settings
) -> None:
    while True:
        try:
            score, presence = compute_presence(state.light_is_bright)
            now = _DateTime.now()
            prev_presence = state.presence

            # Transition OCCUPIED → UNOCCUPIED: end active session
            if prev_presence == "OCCUPIED" and presence != "OCCUPIED":
                if state.desk_session_id is not None and state.desk_session_start is not None:
                    duration = int((now - state.desk_session_start).total_seconds())
                    try:
                        await end_desk_session(state.desk_session_id, now, duration)
                        if duration >= settings.discord.session_end_min_minutes * 60:
                            session_dict = {
                                "start_ts": state.desk_session_start.isoformat(),
                                "end_ts": now.isoformat(),
                                "duration_seconds": duration,
                            }
                            await notification_manager.send_session_end(session_dict)
                    except Exception as exc:
                        logger.error("Failed to finalize desk session %s: %s", state.desk_session_id, exc)
                # Always clear session state regardless of DB/notification errors
                state.desk_session_id = None
                state.desk_session_start = None

            # Transition UNOCCUPIED/UNKNOWN → OCCUPIED: start new session + wake display
            if prev_presence != "OCCUPIED" and presence == "OCCUPIED":
                session_id = await start_desk_session(now)
                state.desk_session_id = session_id
                state.desk_session_start = now
                try:
                    display_queue.put_nowait("presence_return")
                except asyncio.QueueFull:
                    logger.debug("Display queue full on presence return, will render on next cycle")

            state.presence = presence
            state.presence_score = score
            await log_presence(score, presence, "periodic")

            try:
                mqtt_service.publish("home/home_state/presence", {
                    "state": presence,
                    "score": score,
                })
            except Exception as exc:
                logger.warning("Failed to publish presence via MQTT: %s", exc)

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


async def _notification_loop(settings, notification_manager: NotificationManager) -> None:
    last_summary_date = None
    while True:
        await asyncio.sleep(60)
        try:
            await notification_manager.process_retry_queue()

            if settings.discord.notify_daily_summary and settings.discord.daily_summary_time:
                now = _DateTime.now()
                try:
                    h, m = (int(x) for x in settings.discord.daily_summary_time.split(":"))
                    if now.hour == h and now.minute == m and last_summary_date != now.date():
                        yesterday = (now - _timedelta(days=1)).date()
                        sessions = await get_sessions_for_date(yesterday)
                        await notification_manager.send_daily_summary(
                            str(yesterday), sessions
                        )
                        last_summary_date = now.date()
                except ValueError:
                    logger.warning(
                        "Invalid daily_summary_time: %s", settings.discord.daily_summary_time
                    )
        except Exception as exc:
            logger.error("Notification loop error: %s", exc)


async def _display_loop(
    epaper, executor: ThreadPoolExecutor, display_queue: asyncio.Queue, settings
) -> None:
    # Every full_refresh_every-th update is a full refresh (clears ghosting); others use
    # init_fast() for a faster partial update. max(1,...) guards against zero in YAML.
    refresh_count = 0
    loop = asyncio.get_event_loop()

    while True:
        # Align to wall-clock: trigger at :dashboard_trigger_second each minute.
        # Any display_queue event (button, MQTT alert, presence_return) fires immediately.
        now = _DateTime.now()
        target = settings.display.dashboard_trigger_second
        delay = (target - now.second) % 60 or 60  # `or 60` avoids re-triggering immediately
        try:
            await asyncio.wait_for(display_queue.get(), timeout=delay)
        except asyncio.TimeoutError:
            pass  # wall-clock trigger

        if state.presence != "OCCUPIED":
            continue  # pause updates while nobody home

        if state.display_busy:
            continue

        full_refresh = (refresh_count % max(1, settings.display.full_refresh_every) == 0)
        state.display_busy = True
        try:
            # Advance clock by display lag so the rendered HH:MM matches the
            # minute that will be visible when the panel finishes updating.
            render_time = _DateTime.now() + _timedelta(seconds=60 - settings.display.dashboard_trigger_second)
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
    if state.presence != "OCCUPIED" and state.desk_session_id is None:
        now = _DateTime.now()
        try:
            session_id = await start_desk_session(now)
            state.desk_session_id = session_id
            state.desk_session_start = now
        except Exception as exc:
            logger.error("Button: failed to start desk session: %s", exc)
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

    # Recover any session that was still open when the process last stopped
    orphaned = await get_ongoing_desk_session()
    if orphaned:
        from datetime import datetime as _dt_startup
        now_startup = _dt_startup.now()
        duration = int((now_startup - _dt_startup.fromisoformat(orphaned["start_ts"])).total_seconds())
        await end_desk_session(orphaned["id"], now_startup, duration)
        logger.info("Recovered orphaned desk session %s (duration=%ds)", orphaned["id"], duration)

    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="hw")
    display_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    dht22 = create_dht22(settings.sensors.dht22)
    light = create_light_sensor(settings.sensors.light)
    button = create_button(settings.sensors.button)
    epaper = create_epaper(settings.display)
    weather_service = WeatherService(settings.weather)
    voice_service = VoiceService(settings.voice)
    discord_service = DiscordService(settings.discord)
    notification_manager = NotificationManager(discord_service, settings.discord)

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

    # Send device online notification after a short delay (let MQTT connect first)
    if settings.discord.notify_device_online:
        import socket
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            local_ip = settings.webui.host
        webui_url = f"http://{local_ip}:{settings.webui.port}"
        asyncio.get_event_loop().call_later(
            5, lambda: asyncio.ensure_future(
                notification_manager.send_device_online(webui_url)
            )
        )

    try:
        await asyncio.gather(
            _sensor_loop(dht22, light, executor, settings),
            _presence_loop(display_queue, mqtt_service, notification_manager, settings),
            _display_loop(epaper, executor, display_queue, settings),
            _weather_loop(weather_service, settings),
            _notification_loop(settings, notification_manager),
            server.serve(),
        )
    finally:
        mqtt_service.stop()
        executor.shutdown(wait=False)
        await log_system_event("INFO", "main", "ePaper Home Display stopped")


if __name__ == "__main__":
    asyncio.run(main())
