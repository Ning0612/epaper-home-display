from __future__ import annotations

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

_TARGET_W = 280   # IMAGE_W - 2 * PAD
_TARGET_H = 448   # IMAGE_H - 2 * PAD

# Prevent decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 100_000_000  # 100 MP hard limit

_ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF"})
_UPLOAD_CHUNK = 65_536  # 64 KB


def make_display_image(
    source_path: str,
    crop: dict | None = None,
    transform: dict | None = None,
) -> Image.Image:
    """Load image, apply transforms + crop, then resize to 280×448 RGB.

    Transform canonical order: flipX → flipY → rotate CW (must match canvas render order).
    The driver's getbuffer() handles six-color palette quantization internally.

    Returns:
        280×448 RGB mode PIL Image.

    Raises:
        OSError: File cannot be opened or is not a valid image.
        ValueError: Crop region is invalid or format is not allowed.
    """
    with Image.open(source_path) as img:
        img.load()

        if img.format and img.format not in _ALLOWED_FORMATS:
            raise ValueError(f"Unsupported image format: {img.format}")

        # Apply transforms before crop (canonical: flipX → flipY → rotate CW)
        if transform:
            if transform.get("flip_x"):
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if transform.get("flip_y"):
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            rot = int(transform.get("rotate", 0)) % 360
            if rot == 90:
                img = img.transpose(Image.Transpose.ROTATE_270)   # 90 CW = 270 CCW
            elif rot == 180:
                img = img.transpose(Image.Transpose.ROTATE_180)
            elif rot == 270:
                img = img.transpose(Image.Transpose.ROTATE_90)    # 270 CW = 90 CCW

        if crop is not None:
            x, y, w, h = (int(crop[k]) for k in ("x", "y", "w", "h"))
            if w <= 0 or h <= 0:
                raise ValueError(f"Invalid crop: w={w}, h={h}")
            img_w, img_h = img.size
            if x >= 0 and y >= 0 and x + w <= img_w and y + h <= img_h:
                # Fast path: crop is fully within image bounds
                img = img.crop((x, y, x + w, y + h))
            else:
                # Crop extends beyond image bounds; fill out-of-bounds with white
                if w * h > Image.MAX_IMAGE_PIXELS:
                    raise ValueError(
                        f"Crop area too large ({w}×{h}); exceeds pixel limit"
                    )
                canvas = Image.new("RGB", (w, h), (255, 255, 255))
                ix1, iy1 = max(0, x), max(0, y)
                ix2, iy2 = min(img_w, x + w), min(img_h, y + h)
                if ix2 > ix1 and iy2 > iy1:
                    region = img.crop((ix1, iy1, ix2, iy2))
                    canvas.paste(region.convert("RGB"), (ix1 - x, iy1 - y))
                img = canvas

        img = img.convert("RGB")
        img = img.resize((_TARGET_W, _TARGET_H), Image.Resampling.LANCZOS)
        return img


def make_preview_bytes(
    source_path: str,
    crop: dict | None = None,
    transform: dict | None = None,
) -> bytes:
    """Return dithered display image as PNG bytes for HTTP preview response."""
    result = make_display_image(source_path, crop, transform)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
