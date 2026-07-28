from __future__ import annotations

import asyncio
import logging

from app.services.claude_usage import ClaudeUsageService, _RateLimitedError
from app.state import state

logger = logging.getLogger(__name__)

_CREDS_RETRY_INTERVAL = 60
_RATE_LIMIT_BUFFER = 5      # wake a little after the cooldown, not exactly on it
_RATE_LIMIT_MAX_WAIT = 3600  # ceiling, so an absurd Retry-After can't stall the loop


def _backoff_seconds(default_wait: int, retry_after: int | None) -> int:
    """How long to sleep after a 429: at least the poll interval, and long enough
    to clear the server's Retry-After cooldown (plus a small buffer)."""
    if retry_after is None:
        return default_wait
    return min(_RATE_LIMIT_MAX_WAIT, max(default_wait, retry_after + _RATE_LIMIT_BUFFER))


async def _claude_usage_loop(service: ClaudeUsageService, settings) -> None:
    logger.info("Claude usage collection started (poll_interval=%ds)", settings.claude_usage.poll_interval_seconds)

    while True:
        if not service.load_credentials():
            logger.warning(
                "claude_creds.json not found or invalid — retrying in %ds "
                "(run tools/claude_auth.py on laptop to authorise)",
                _CREDS_RETRY_INTERVAL,
            )
            await asyncio.sleep(_CREDS_RETRY_INTERVAL)
            continue

        wait = max(60, min(1800, settings.claude_usage.poll_interval_seconds))

        try:
            data = await service.fetch_usage()
            if data is not None:
                state.claude_usage_5h = data.usage_5h
                state.claude_usage_week = data.usage_7d
                state.claude_5h_reset = data.reset_5h
                state.claude_7d_reset = data.reset_7d
                logger.info(
                    "Claude usage: 5h=%.0f%% 7d=%.0f%% reset_5h=%s",
                    data.usage_5h * 100,
                    data.usage_7d * 100,
                    data.reset_5h,
                )
        except _RateLimitedError as exc:
            # This endpoint's cooldown routinely exceeds the poll interval. Retrying
            # before it expires just earns another 429, so the loop never recovers —
            # honour Retry-After instead of polling straight through it.
            wait = _backoff_seconds(wait, exc.retry_after)
        except Exception as exc:
            logger.warning("Claude usage loop error: %s", exc)

        await asyncio.sleep(wait)
