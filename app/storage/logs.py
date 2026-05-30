from __future__ import annotations

# 向後相容 re-export 層：所有外部呼叫點繼續從此處 import，無需修改。
from app.storage._log_helpers import _now, _to_iso, _safe_json_loads
from app.storage._log_events import (
    log_env,
    log_presence,
    log_door_event,
    log_face_event,
    log_alarm_decision,
    log_system_event,
    log_ai_usage,
    get_recent_door_events,
    get_recent_face_events,
    get_env_logs,
    get_presence_logs,
    get_system_events,
)
from app.storage._log_sessions import (
    start_desk_session,
    end_desk_session,
    get_ongoing_desk_session,
    get_sessions_for_date,
    get_sessions_last_n_days,
    get_recent_sessions,
)
from app.storage._log_notifications import (
    queue_notification,
    get_pending_notifications,
    mark_notification_sent,
    update_notification_retry,
)

__all__ = [
    "_now",
    "_to_iso",
    "_safe_json_loads",
    "log_env",
    "log_presence",
    "log_door_event",
    "log_face_event",
    "log_alarm_decision",
    "log_system_event",
    "log_ai_usage",
    "get_recent_door_events",
    "get_recent_face_events",
    "get_env_logs",
    "get_presence_logs",
    "get_system_events",
    "start_desk_session",
    "end_desk_session",
    "get_ongoing_desk_session",
    "get_sessions_for_date",
    "get_sessions_last_n_days",
    "get_recent_sessions",
    "queue_notification",
    "get_pending_notifications",
    "mark_notification_sent",
    "update_notification_retry",
]
