from __future__ import annotations

# 向後相容 re-export 層：所有外部呼叫點繼續從此處 import，無需修改。
from app.storage._log_helpers import _now, _to_iso, _safe_json_loads
from app.storage._log_events import (
    log_env,
    log_presence,
    log_system_event,
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
    get_sessions_overlapping,
    get_recent_sessions,
)
from app.storage._log_notifications import (
    queue_notification,
    get_pending_notifications,
    mark_notification_sent,
    update_notification_retry,
)
from app.storage._log_images import (
    add_image,
    confirm_image,
    list_images,
    get_image,
    delete_image_record,
    count_confirmed_images,
    get_oldest_confirmed_image,
    get_unconfirmed_images,
)
from app.storage._log_env_analytics import (
    get_env_daily,
    get_env_monthly,
    get_env_yearly,
    get_env_today_extremes,
    get_available_years,
)

__all__ = [
    "_now",
    "_to_iso",
    "_safe_json_loads",
    "log_env",
    "log_presence",
    "log_system_event",
    "get_env_logs",
    "get_presence_logs",
    "get_system_events",
    "start_desk_session",
    "end_desk_session",
    "get_ongoing_desk_session",
    "get_sessions_for_date",
    "get_sessions_last_n_days",
    "get_sessions_overlapping",
    "get_recent_sessions",
    "queue_notification",
    "get_pending_notifications",
    "mark_notification_sent",
    "update_notification_retry",
    "add_image",
    "confirm_image",
    "list_images",
    "get_image",
    "delete_image_record",
    "count_confirmed_images",
    "get_oldest_confirmed_image",
    "get_unconfirmed_images",
    "get_env_daily",
    "get_env_monthly",
    "get_env_yearly",
    "get_env_today_extremes",
    "get_available_years",
]
