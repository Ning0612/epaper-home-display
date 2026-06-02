from __future__ import annotations

import asyncio
import logging

from app.services.claude_usage import ClaudeUsageService, _RateLimitedError
from app.state import state

logger = logging.getLogger(__name__)

_CREDS_RETRY_INTERVAL = 60


async def _claude_usage_loop(service: ClaudeUsageService, settings) -> None:
    poll_interval = max(60, settings.claude_usage.poll_interval_seconds)
    logger.info("Claude usage collection started (poll_interval=%ds)", poll_interval)

    while True:
        if not service.load_credentials():
            logger.warning(
                "claude_creds.json not found or invalid — retrying in %ds "
                "(run tools/claude_auth.py on laptop to authorise)",
                _CREDS_RETRY_INTERVAL,
            )
            await asyncio.sleep(_CREDS_RETRY_INTERVAL)
            continue

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
        except _RateLimitedError:
            pass
        except Exception as exc:
            logger.warning("Claude usage loop error: %s", exc)

        await asyncio.sleep(poll_interval)
