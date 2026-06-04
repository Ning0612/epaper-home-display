from __future__ import annotations

import asyncio
import logging
from datetime import datetime as _DateTime

from app.state import state
from app.storage.logs import start_desk_session

logger = logging.getLogger(__name__)

# Minimum seconds between manual alarm re-triggers via button 3 (prevents MQTT/voice spam).
_ALERT_REFRESH_COOLDOWN_SECS = 180


def _in_ap_mode(btn_num: int) -> bool:
    if state.wifi_mode == "ap":
        logger.debug("Button %d ignored: device in AP mode", btn_num)
        return True
    return False


def _alert_within_cooldown(now: _DateTime) -> bool:
    """Return True if the last alert refresh is within the cooldown window."""
    if state.alert_last_triggered_at is None:
        return False
    return (now - state.alert_last_triggered_at).total_seconds() < _ALERT_REFRESH_COOLDOWN_SECS


async def _handle_btn_dashboard(display_queue: asyncio.Queue) -> None:
    """Button 1 (GPIO 5) — force OCCUPIED and switch to Dashboard.

    Clears alert state when transitioning from the alert page so that
    presence_loop does not continue acting on stale alert data.
    """
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
    if state.display_page == "alert":
        state.last_snapshot_image = None
        state.last_alarm_decision = None
        state.last_alert = None
        state.alert_face_event = None
        state.alert_last_triggered_at = None
        state.alert_page_started_at = None
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
    voice_service,
    mqtt_service,
) -> None:
    """Button 3 (GPIO 22) — re-send alarm signal while on the alert page.

    Only activates when already on the alert page (entered via MQTT alert).
    Does NOT switch pages or push to the display queue; only publishes to
    home/home_state/alarm_decision and plays the voice alert.
    Repeated presses within _ALERT_REFRESH_COOLDOWN_SECS are ignored to
    prevent MQTT and voice spam.
    """
    if _in_ap_mode(3):
        return
    if state.display_page != "alert":
        logger.debug("Button 3 ignored: not on alert page")
        return
    now = _DateTime.now()
    if _alert_within_cooldown(now):
        logger.debug(
            "Button 3 ignored: within %ds cooldown", _ALERT_REFRESH_COOLDOWN_SECS
        )
        return
    state.alert_last_triggered_at = now
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
    logger.info("Button 3: alarm re-triggered (MQTT + voice, no display change)")


async def _handle_btn_cancel_alarm(mqtt_service) -> None:
    """Button 4 (GPIO 27) — send cancel signal while on the alert page.

    Only activates when already on the alert page.
    Does NOT switch pages or clear state; only publishes
    home/home_state/alarm_decision with decision=cancel.
    """
    if _in_ap_mode(4):
        return
    if state.display_page != "alert":
        logger.debug("Button 4 ignored: not on alert page")
        return
    if mqtt_service is not None:
        try:
            mqtt_service.publish("home/home_state/alarm_decision", {
                "decision": "cancel",
                "source": "button",
            })
        except Exception as exc:
            logger.error("Button 4: MQTT publish failed: %s", exc)
    logger.info("Button 4: alarm cancel signal sent")
