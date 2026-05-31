from __future__ import annotations

import asyncio
import io
import logging

import aiohttp

logger = logging.getLogger(__name__)

# Outdoor agent snapshots are QVGA JPEG — reject anything larger than 1 MB to guard
# against a misconfigured or compromised endpoint returning an unexpectedly large payload.
_MAX_SNAPSHOT_BYTES = 1_048_576   # 1 MB

# Module-level persistent session reused across 3-second refresh cycles to avoid
# the overhead of TCP setup/teardown and mDNS re-resolution on every request.
_session: aiohttp.ClientSession | None = None


def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(limit=1)
        _session = aiohttp.ClientSession(connector=connector)
    return _session


async def close_session() -> None:
    """Gracefully close the shared HTTP session. Call on application shutdown."""
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def fetch_snapshot(url: str, timeout_sec: float = 2.5):
    """Fetch a JPEG snapshot from the outdoor agent HTTP endpoint.

    Returns a PIL Image (RGB mode) on success, or None on any failure
    (network error, timeout, oversized payload, non-image response, etc.) — never raises.
    """
    if not url:
        return None
    try:
        session = _get_session()
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status != 200:
                logger.debug("Snapshot HTTP %d from %s", resp.status, url)
                return None
            ct = resp.content_type or ""
            if not ct.startswith("image/"):
                logger.warning("Snapshot unexpected content-type %r from %s", ct, url)
                return None
            data = await resp.content.read(_MAX_SNAPSHOT_BYTES + 1)
            if len(data) > _MAX_SNAPSHOT_BYTES:
                logger.warning(
                    "Snapshot response too large (>%d B) from %s, skipping",
                    _MAX_SNAPSHOT_BYTES, url,
                )
                return None

        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img.load()
        return img.convert("RGB")

    except aiohttp.ClientError as exc:
        logger.debug("Snapshot network error: %s", exc)
    except asyncio.TimeoutError:
        logger.debug("Snapshot timeout (%.1fs) from %s", timeout_sec, url)
    except Exception as exc:
        logger.warning("Snapshot unexpected error: %s", exc)
    return None
