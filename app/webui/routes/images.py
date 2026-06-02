from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.state import state
from app.webui.config_helpers import _save_to_config
from app.webui.models import _CarouselBody, _ConfirmBody, _PreviewBody
from app.webui.templates.images import _IMAGES_HTML

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

_CHUNK = 65_536  # 64 KB chunks for streaming upload


def create_images_router(
    settings: "Settings",
    display_queue: "asyncio.Queue | None" = None,
) -> APIRouter:
    router = APIRouter()

    def _tmp_dir() -> str:
        p = os.path.join(settings.images.storage_dir, "tmp")
        os.makedirs(p, exist_ok=True)
        return p

    def _img_dir() -> str:
        os.makedirs(settings.images.storage_dir, exist_ok=True)
        return settings.images.storage_dir

    def _allowed_mimes() -> frozenset[str]:
        fmt_to_mime = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "GIF": "image/gif",
            "BMP": "image/bmp",
            "TIFF": "image/tiff",
        }
        return frozenset(
            fmt_to_mime[f] for f in settings.images.allowed_formats if f in fmt_to_mime
        )

    # ------------------------------------------------------------------ pages
    @router.get("/images", response_class=HTMLResponse)
    async def images_page():
        return HTMLResponse(_IMAGES_HTML)

    # ------------------------------------------------------------------ file serving
    @router.get("/api/images/file/{id}")
    async def serve_display_image(id: str):
        from app.storage._log_images import get_image
        row = await get_image(id)
        if row is None or row["tmp_path"] is not None:
            raise HTTPException(404, "Image not found")
        path = row["display_path"]
        if not os.path.exists(path):
            raise HTTPException(404, "Image file missing")
        _assert_within_storage(path, settings.images.storage_dir)
        return FileResponse(path, media_type="image/png")

    @router.get("/api/images/original/{id}")
    async def serve_original_image(id: str):
        from app.storage._log_images import get_image
        row = await get_image(id)
        if row is None:
            raise HTTPException(404, "Image not found")
        path = row["tmp_path"] or row["display_path"]
        if not path or not os.path.exists(path):
            raise HTTPException(404, "Original file missing")
        _assert_within_storage(path, settings.images.storage_dir)
        import mimetypes
        mime, _ = mimetypes.guess_type(path)
        return FileResponse(path, media_type=mime or "application/octet-stream")

    # ------------------------------------------------------------------ image list
    @router.get("/api/images")
    async def list_images_api():
        from app.storage._log_images import list_images
        images = await list_images()
        current = state.custom_image_path
        return {
            "images": [
                {
                    "id": img["id"],
                    "filename": img["filename"],
                    "file_size": img["file_size"],
                    "created_ts": img["created_ts"],
                    "is_current": (img["display_path"] == current),
                }
                for img in images
            ]
        }

    # ------------------------------------------------------------------ upload
    @router.post("/api/images/upload")
    async def upload_image(file: UploadFile = File(...)):
        allowed = _allowed_mimes()
        content_type = (file.content_type or "").split(";")[0].strip()
        if content_type and content_type not in allowed:
            raise HTTPException(400, f"Unsupported file type: {content_type}")

        img_id = str(uuid.uuid4())
        orig_name = file.filename or "upload"
        _, ext = os.path.splitext(orig_name)
        ext = ext.lower()[:10] if ext else ".bin"
        tmp_path = os.path.join(_tmp_dir(), f"{img_id}{ext}")

        # Stream upload to disk in chunks
        try:
            written = await _write_chunked(file, tmp_path, settings.images.max_upload_bytes)
        except ValueError as exc:
            raise HTTPException(413, str(exc)) from exc
        except OSError as exc:
            logger.error("Failed to write upload: %s", exc)
            raise HTTPException(500, "Upload write failed") from exc

        # Validate image in a thread (CPU-bound, avoids blocking event loop)
        try:
            orig_w, orig_h = await asyncio.to_thread(
                _validate_image_sync, tmp_path, settings.images.max_pixels,
                frozenset(settings.images.allowed_formats),
            )
        except (ValueError, Exception) as exc:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise HTTPException(400, f"Invalid image: {exc}") from exc

        # Insert pending record
        from app.storage._log_images import add_image
        display_path = os.path.join(_img_dir(), f"{img_id}_display.png")
        await add_image(img_id, orig_name, display_path, tmp_path, written)

        return {"id": img_id, "orig_w": orig_w, "orig_h": orig_h}

    # ------------------------------------------------------------------ preview
    @router.post("/api/images/preview")
    async def preview_dithered(body: _PreviewBody):
        from app.storage._log_images import get_image
        row = await get_image(body.id)
        if row is None:
            raise HTTPException(404, "Upload not found")

        src = row["tmp_path"] or row["display_path"]
        if not src or not os.path.exists(src):
            raise HTTPException(404, "Source file missing")
        _assert_within_storage(src, settings.images.storage_dir)

        crop = {"x": body.crop.x, "y": body.crop.y, "w": body.crop.w, "h": body.crop.h}
        tf = body.transform.model_dump()
        try:
            from app.display.image_processor import make_preview_bytes
            png_bytes = await asyncio.to_thread(make_preview_bytes, src, crop, tf)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            logger.error("Preview generation failed: %s", exc)
            raise HTTPException(500, "Preview failed") from exc

        return Response(content=png_bytes, media_type="image/png")

    # ------------------------------------------------------------------ confirm
    @router.post("/api/images/{id}/confirm")
    async def confirm_image_api(id: str, body: _ConfirmBody):
        from app.storage._log_images import (
            get_image, confirm_image, count_confirmed_images,
            get_oldest_confirmed_image, delete_image_record,
        )

        row = await get_image(id)
        if row is None:
            raise HTTPException(404, "Upload not found")

        src = row["tmp_path"] or row["display_path"]
        if not src or not os.path.exists(src):
            raise HTTPException(404, "Source file missing")
        _assert_within_storage(src, settings.images.storage_dir)

        crop = {"x": body.crop.x, "y": body.crop.y, "w": body.crop.w, "h": body.crop.h}
        tf = body.transform.model_dump()
        display_path = os.path.join(_img_dir(), f"{id}_display.png")
        # Use per-request unique tmp to prevent concurrent confirm collisions
        tmp_out = display_path + f".{uuid.uuid4().hex[:8]}.tmp"

        # Generate dithered display PNG in a thread
        try:
            from app.display.image_processor import make_display_image
            result_img = await asyncio.to_thread(make_display_image, src, crop, tf)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            logger.error("Image processing failed: %s", exc)
            raise HTTPException(500, "Image processing failed") from exc

        # Atomic write: unique .tmp → final (also CPU-bound I/O, run in thread)
        try:
            file_size = await asyncio.to_thread(
                _save_display_atomic, result_img, tmp_out, display_path
            )
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(tmp_out)
            raise HTTPException(500, "File write failed") from exc

        # Remove original tmp upload
        if row["tmp_path"] and os.path.exists(row["tmp_path"]):
            with contextlib.suppress(OSError):
                os.unlink(row["tmp_path"])

        # Update DB; on failure, clean up the written file to avoid orphan
        try:
            await confirm_image(id, display_path, file_size)
        except Exception as exc:
            with contextlib.suppress(OSError):
                os.unlink(display_path)
            logger.error("DB confirm failed: %s", exc)
            raise HTTPException(500, "Database update failed") from exc

        # Enforce max_count
        count = await count_confirmed_images()
        if count > settings.images.max_count:
            oldest = await get_oldest_confirmed_image()
            if oldest and oldest["id"] != id:
                deleted = await delete_image_record(oldest["id"])
                if deleted:
                    _remove_image_files(deleted, settings.images.storage_dir)
                    dp = deleted.get("display_path")
                    if dp in state.image_playlist:
                        state.image_playlist = [p for p in state.image_playlist if p != dp]

        # Update carousel state
        if display_path not in state.image_playlist:
            state.image_playlist = state.image_playlist + [display_path]
        state.custom_image_path = display_path
        state.carousel_index = state.image_playlist.index(display_path)
        # Reset advance timer so new image stays visible for at least one interval
        state.carousel_last_advance = datetime.now()

        # Trigger immediate display refresh
        if display_queue is not None:
            with contextlib.suppress(Exception):
                display_queue.put_nowait("image_confirmed")

        return {"ok": True, "id": id}

    # ------------------------------------------------------------------ delete
    @router.delete("/api/images/{id}")
    async def delete_image_api(id: str):
        from app.storage._log_images import get_image, delete_image_record

        row = await get_image(id)
        if row is None:
            raise HTTPException(404, "Image not found")

        # Delete from DB first (reversible on failure — state unchanged)
        deleted = await delete_image_record(id)
        if deleted is None:
            raise HTTPException(500, "Delete failed")

        # Update in-memory state AFTER DB is clean
        dp = deleted.get("display_path")
        is_current = (dp == state.custom_image_path)
        new_playlist = [p for p in state.image_playlist if p != dp]
        state.image_playlist = new_playlist

        if is_current:
            state.custom_image_path = new_playlist[0] if new_playlist else None
            state.carousel_index = 0

        # Remove files last (orphan tolerable, inconsistent state is not)
        _remove_image_files(deleted, settings.images.storage_dir)

        return {"ok": True}

    # ------------------------------------------------------------------ carousel
    @router.get("/api/images/carousel")
    async def get_carousel():
        return {
            "enabled": settings.images.carousel_enabled,
            "interval_minutes": settings.images.carousel_interval_minutes,
            "mode": settings.images.carousel_mode,
        }

    @router.put("/api/images/carousel")
    async def update_carousel(body: _CarouselBody):
        updates: dict = {}
        if body.enabled is not None:
            settings.images.carousel_enabled = body.enabled
            updates["carousel_enabled"] = body.enabled
        if body.interval_minutes is not None:
            val = max(1, body.interval_minutes)
            settings.images.carousel_interval_minutes = val
            updates["carousel_interval_minutes"] = val
        if body.mode is not None:
            if body.mode not in ("sequential", "random"):
                raise HTTPException(400, "mode must be 'sequential' or 'random'")
            settings.images.carousel_mode = body.mode
            updates["carousel_mode"] = body.mode

        if updates:
            _save_to_config({"images": updates})
        return {"ok": True}

    @router.put("/api/images/carousel/advance")
    async def advance_carousel():
        if len(state.image_playlist) < 2:
            raise HTTPException(400, "Need at least 2 images to advance")

        prev_path = state.custom_image_path
        # Force advance by clearing last_advance timestamp
        state.carousel_last_advance = None
        from app.loops.display import _maybe_advance_carousel
        _maybe_advance_carousel(settings)

        changed = state.custom_image_path != prev_path
        if display_queue is not None and changed:
            with contextlib.suppress(Exception):
                display_queue.put_nowait("carousel_advance")

        return {"ok": True, "changed": changed, "current": state.custom_image_path}

    return router


# ------------------------------------------------------------------ sync helpers (run in threads)

def _validate_image_sync(
    tmp_path: str, max_pixels: int, allowed_formats: frozenset[str]
) -> tuple[int, int]:
    from PIL import Image as _PILImage
    with _PILImage.open(tmp_path) as pimg:
        pimg.verify()
    with _PILImage.open(tmp_path) as pimg2:
        actual_fmt = (pimg2.format or "").upper()
        if actual_fmt not in allowed_formats:
            raise ValueError(f"Image format {actual_fmt!r} not allowed")
        w, h = pimg2.size
        if w * h > max_pixels:
            raise ValueError(f"Image too large ({w}×{h}, max {max_pixels:,} pixels)")
        return w, h


def _is_within_storage(path: str, storage_dir: str) -> bool:
    real_path = os.path.realpath(path)
    real_storage = os.path.realpath(storage_dir)
    return real_path == real_storage or real_path.startswith(real_storage + os.sep)


def _assert_within_storage(path: str, storage_dir: str) -> None:
    """Raise 403 if path is not within storage_dir (guards against DB-path traversal)."""
    if not _is_within_storage(path, storage_dir):
        raise HTTPException(403, "File access denied")


def _save_display_atomic(img, tmp_out: str, display_path: str) -> int:
    img.save(tmp_out, format="PNG")
    os.replace(tmp_out, display_path)
    return os.path.getsize(display_path)


# ------------------------------------------------------------------ async helpers

def _remove_image_files(row: dict, storage_dir: str) -> None:
    for key in ("display_path", "tmp_path"):
        path = row.get(key)
        if path and _is_within_storage(path, storage_dir):
            with contextlib.suppress(OSError):
                os.unlink(path)
        elif path:
            logger.warning("Skipping delete of path outside storage: %s", path)


async def _write_chunked(upload: UploadFile, dest: str, max_bytes: int) -> int:
    """Stream upload file to dest in chunks; raises ValueError if max_bytes exceeded."""
    written = 0
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = await upload.read(_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError(
                        f"Upload exceeds {max_bytes // 1_048_576} MB limit"
                    )
                f.write(chunk)
    except ValueError:
        with contextlib.suppress(OSError):
            os.unlink(dest)
        raise
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(dest)
        raise
    return written
