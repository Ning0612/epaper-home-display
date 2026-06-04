from __future__ import annotations

import asyncio
import logging
from datetime import datetime as _DateTime

from app.state import state
from app.storage.logs import start_desk_session

logger = logging.getLogger(__name__)


def _in_ap_mode(btn_num: int) -> bool:
    if state.wifi_mode == "ap":
        logger.debug("Button %d ignored: device in AP mode", btn_num)
        return True
    return False


async def _handle_btn_dashboard(display_queue: asyncio.Queue) -> None:
    """Button 1 (GPIO 5) — force OCCUPIED and switch to Dashboard."""
    if _in_ap_mode(1):
        return
    if state.presence != "OCCUPIED" and state.desk_session_id is None:
        now = _DateTime.now()
        try:
            session_id = await start_desk_session(now)
            state.desk_session_id = session_id
            state.desk_session_start = now
        except Exception as exc:
            logger.error("Button 1: failed to start desk session: %s", exc)
    state.presence = "OCCUPIED"
    state.display_page = "dashboard"
    try:
        display_queue.put_nowait("dashboard")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button 1 press")
    logger.info("Button 1: OCCUPIED + dashboard")


async def _handle_btn_alert_page(display_queue: asyncio.Queue) -> None:
    """Button 2 (GPIO 6) — switch to Alert page."""
    if _in_ap_mode(2):
        return
    now = _DateTime.now()
    if state.display_page != "alert":
        state.alert_page_started_at = now
    state.alert_last_triggered_at = now
    state.display_page = "alert"
    try:
        display_queue.put_nowait("alert")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button 2 press")
    logger.info("Button 2: switched to alert page")


async def _handle_btn_trigger_alarm(
    display_queue: asyncio.Queue,
    voice_service,
    mqtt_service,
) -> None:
    """Button 3 (GPIO 22) — manually trigger alarm.

    Publishes to home/home_state/alarm_decision (not home/security/alert) to avoid
    self-echo: the device subscribes to home/security/alert, so publishing there would
    re-trigger state updates and double the voice alert.
    """
    if _in_ap_mode(3):
        return
    now = _DateTime.now()
    if state.display_page != "alert":
        state.alert_page_started_at = now
    state.alert_last_triggered_at = now
    state.display_page = "alert"
    try:
        display_queue.put_nowait("alert")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button 3 press")
    if mqtt_service is not None:
        try:
            mqtt_service.publish("home/home_state/alarm_decision", {
                "decision": "manual_trigger",
                "source": "button",
            })
        except Exception as exc:
            logger.error("Button 3: MQTT publish failed: %s", exc)
    if voice_service is not None:
        await voice_service.play("alert.wav")
    logger.info("Button 3: manual alarm triggered")


async def _handle_btn_cancel_alarm(display_queue: asyncio.Queue, mqtt_service) -> None:
    """Button 4 (GPIO 27) — cancel alarm and return to Dashboard."""
    if _in_ap_mode(4):
        return
    state.display_page = "dashboard"
    state.last_snapshot_image = None
    state.alert_last_triggered_at = None
    state.alert_page_started_at = None
    try:
        display_queue.put_nowait("dashboard")
    except asyncio.QueueFull:
        logger.debug("Display queue full on button 4 press")
    if mqtt_service is not None:
        try:
            mqtt_service.publish("home/home_state/alarm_decision", {
                "decision": "cancel",
                "source": "button",
            })
        except Exception as exc:
            logger.error("Button 4: MQTT publish failed: %s", exc)
    logger.info("Button 4: alarm cancelled")
