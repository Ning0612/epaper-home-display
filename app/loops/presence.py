from __future__ import annotations

import asyncio
import logging
from datetime import datetime as _DateTime

from app.logic.alarm_decision import compute_alarm_decision
from app.logic.presence import compute_presence
from app.logic.reminder import generate_reminder
from app.services.notification_manager import NotificationManager
from app.state import state
from app.storage.logs import end_desk_session, log_alarm_decision, log_presence, start_desk_session

logger = logging.getLogger(__name__)


async def _presence_loop(
    display_queue: asyncio.Queue, mqtt_service, notification_manager: NotificationManager, settings
) -> None:
    # Publish alarm_decision only when the alert object changes (new event) or the
    # decision/reason changes (presence shift for the same alert).
    # Using object identity avoids relying on timestamp format or uniqueness.
    _last_processed_alert: dict | None = None
    _last_published_decision: tuple | None = None  # (decision, reason)

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
                alert = state.last_alert
                decision, reason = compute_alarm_decision(
                    presence, score, alert, state.last_face_event
                )
                state.last_alarm_decision = decision
                await log_alarm_decision(decision, reason, score)
                if alert is not _last_processed_alert or (decision, reason) != _last_published_decision:
                    try:
                        mqtt_service.publish("home/home_state/alarm_decision", {
                            "decision": decision,
                            "reason": reason,
                            "score": score,
                        })
                        _last_processed_alert = alert
                        _last_published_decision = (decision, reason)
                    except Exception as exc:
                        logger.warning("Failed to publish alarm_decision via MQTT: %s", exc)
        except Exception as exc:
            logger.error("Presence loop error: %s", exc)
        await asyncio.sleep(60)
