from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as _DateTime

import uvicorn

from app.config import load_settings
from app.display.epaper import create_epaper
from app.loops.button import _handle_button
from app.loops.display import _display_loop
from app.loops.notification import _notification_loop
from app.loops.presence import _presence_loop
from app.loops.sensor import _sensor_loop
from app.loops.weather import _weather_loop
from app.sensors.button import create_button
from app.sensors.dht22 import create_dht22
from app.sensors.light_sensor import create_light_sensor
from app.services.discord import DiscordService
from app.services.mqtt_client import MQTTService, make_done_callback
from app.services.notification_manager import NotificationManager
from app.services.voice import VoiceService
from app.services.weather import WeatherService
from app.services.wifi_monitor import _wifi_monitor_loop
from app.state import state
from app.storage.db import init_db
from app.storage.logs import end_desk_session, get_ongoing_desk_session, list_images, log_system_event
from app.storage._log_images import get_unconfirmed_images, delete_image_record
from app.webui.server import create_app

logger = logging.getLogger(__name__)


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
    await _init_image_state(settings)

    # Recover any session that was still open when the process last stopped
    orphaned = await get_ongoing_desk_session()
    if orphaned:
        now_startup = _DateTime.now()
        duration = int((now_startup - _DateTime.fromisoformat(orphaned["start_ts"])).total_seconds())
        await end_desk_session(orphaned["id"], now_startup, duration)
        logger.info("Recovered orphaned desk session %s (duration=%ds)", orphaned["id"], duration)

    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="hw")
    display_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

    dht22 = create_dht22(settings.sensors.dht22)
    light = create_light_sensor(settings.sensors.light)
    button = create_button(settings.sensors.button)
    epaper = create_epaper(settings.display)
    weather_service = WeatherService(settings.weather)
    voice_service = VoiceService(settings.voice)
    discord_service = DiscordService(settings.discord)
    notification_manager = NotificationManager(discord_service, settings.discord)

    loop = asyncio.get_running_loop()
    mqtt_service = MQTTService(settings.mqtt, display_queue, voice_service)
    mqtt_service.start(loop)

    def _on_button():
        future = asyncio.run_coroutine_threadsafe(_handle_button(display_queue), loop)
        future.add_done_callback(make_done_callback("Button callback"))

    button.register_callback(_on_button)

    uvicorn_config = uvicorn.Config(
        create_app(settings, weather_service, display_queue),
        host=settings.webui.host,
        port=settings.webui.port,
        log_level="warning",
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("WebUI → http://%s:%d", settings.webui.host, settings.webui.port)

    if settings.discord.notify_device_online:
        local_ip: str | None = None
        try:
            # Connect a UDP socket to determine the outbound LAN IP.
            # No data is sent; the OS selects the correct routing interface.
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as _s:
                _s.connect(("8.8.8.8", 80))
                local_ip = _s.getsockname()[0]
        except Exception:
            pass
        # Fallback: use configured host if it is a real address; otherwise use mDNS hostname.
        if not local_ip or local_ip.startswith(("0.", "127.")):
            h = settings.webui.host
            local_ip = h if (h and h not in ("0.0.0.0",) and not h.startswith("127.")) else "epaper-display.local"
        webui_url = f"http://{local_ip}:{settings.webui.port}"
        loop.call_later(
            5, lambda: asyncio.ensure_future(
                notification_manager.send_device_online(webui_url)
            )
        )

    try:
        await asyncio.gather(
            _sensor_loop(dht22, light, executor, settings),
            _presence_loop(display_queue, mqtt_service, notification_manager, settings),
            _display_loop(epaper, executor, display_queue, settings, mqtt_service),
            _weather_loop(weather_service, settings),
            _notification_loop(settings, notification_manager),
            _wifi_monitor_loop(display_queue, settings),
            server.serve(),
        )
    finally:
        mqtt_service.stop()
        executor.shutdown(wait=False)
        await log_system_event("INFO", "main", "ePaper Home Display stopped")


async def _init_image_state(settings) -> None:
    """Clean orphan uploads, load confirmed images into state.image_playlist."""
    # Remove orphan uploads (interrupted before confirm)
    orphans = await get_unconfirmed_images()
    for orphan in orphans:
        try:
            if orphan["tmp_path"] and os.path.exists(orphan["tmp_path"]):
                os.unlink(orphan["tmp_path"])
        except OSError:
            pass
        await delete_image_record(orphan["id"])
    if orphans:
        logger.info("Cleaned up %d orphan image uploads", len(orphans))

    # Load confirmed images; skip any with missing files
    images = await list_images()
    valid_paths = [img["display_path"] for img in images if os.path.exists(img["display_path"])]
    state.image_playlist = valid_paths
    if valid_paths:
        state.custom_image_path = valid_paths[0]
    logger.info("Image playlist loaded: %d image(s)", len(valid_paths))


if __name__ == "__main__":
    asyncio.run(main())
