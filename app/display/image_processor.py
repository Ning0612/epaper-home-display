from __future__ import annotations

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

_TARGET_W = 280   # IMAGE_W - 2 * PAD
_TARGET_H = 448   # IMAGE_H - 2 * PAD

# Prevent decompression bomb / memory exhaustion on Pi Zero 2W
Image.MAX_IMAGE_PIXELS = 25_000_000  # 25 MP hard limit

# Mirrors epd7in3e.py getbuffer() palette — keep in sync with the hardware driver.
# Slot 4 is the Orange placeholder (commented out in the driver); filled with Black.
_EPAPER_PALETTE_RGB: tuple[int, ...] = (
    0,   0,   0,    # 0 Black
    255, 255, 255,  # 1 White
    255, 255, 0,    # 2 Yellow
    255, 0,   0,    # 3 Red
    0,   0,   0,    # 4 Orange (unused → Black)
    0,   0,   255,  # 5 Blue
    0,   255, 0,    # 6 Green
) + (0, 0, 0) * 249


def quantize_to_epaper_palette(img: Image.Image) -> Image.Image:
    """Quantize an RGB image to the 6-color e-paper palette with Floyd-Steinberg dithering."""
    pal = Image.new("P", (1, 1))
    pal.putpalette(_EPAPER_PALETTE_RGB)
    return img.convert("RGB").quantize(palette=pal).convert("RGB")


_BW_PALETTE_RGB: tuple[int, ...] = (
    0,   0,   0,    # 0 Black
    255, 255, 255,  # 1 White
) + (0, 0, 0) * 254


def quantize_to_bw_palette(img: Image.Image) -> Image.Image:
    """Quantize an RGB image to black-and-white with Floyd-Steinberg dithering."""
    pal = Image.new("P", (1, 1))
    pal.putpalette(_BW_PALETTE_RGB)
    return img.convert("RGB").quantize(palette=pal).convert("RGB")

_ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF"})
_FIT_MODES = frozenset({"crop", "contain", "stretch"})
_UPLOAD_CHUNK = 65_536  # 64 KB


def make_display_image(
    source_path: str,
    crop: dict | None = None,
    transform: dict | None = None,
    fit: str = "crop",
) -> Image.Image:
    """Load image, apply transforms and fit it into a 280×448 RGB image.

    Transform canonical order: flipX → flipY → rotate CW (must match canvas render order).
    ``crop`` is used only for ``fit="crop"``. ``contain`` preserves the transformed
    image's aspect ratio and pads with white; ``stretch`` resizes directly to the
    target dimensions. A missing crop in crop mode keeps the legacy full-image resize
    behavior for direct callers.
    The driver's getbuffer() handles six-color palette quantization internally.

    Returns:
        280×448 RGB mode PIL Image.

    Raises:
        OSError: File cannot be opened or is not a valid image.
        ValueError: Crop region, fit mode, or format is invalid.
    """
    if not isinstance(fit, str) or fit not in _FIT_MODES:
        raise ValueError("fit must be 'crop', 'contain', or 'stretch'")

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

        if fit == "crop" and crop is not None:
            try:
                x, y, w, h = (int(crop[k]) for k in ("x", "y", "w", "h"))
            except OverflowError as exc:
                raise ValueError("Crop coordinates out of range") from exc
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
        if fit == "contain":
            scale = min(_TARGET_W / img.width, _TARGET_H / img.height)
            size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
            fitted = img.resize(size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (_TARGET_W, _TARGET_H), (255, 255, 255))
            canvas.paste(fitted, ((_TARGET_W - size[0]) // 2, (_TARGET_H - size[1]) // 2))
            return canvas

        return img.resize((_TARGET_W, _TARGET_H), Image.Resampling.LANCZOS)


def make_preview_bytes(
    source_path: str,
    crop: dict | None = None,
    transform: dict | None = None,
    panel_type: str = "color",
    fit: str = "crop",
) -> bytes:
    """Return dithered display image as PNG bytes for HTTP preview response.

    panel_type="color": 6-color e-paper palette (epd7in3e)
    panel_type="bw":    black-and-white palette (epd7in5_V2)
    """
    result = make_display_image(source_path, crop, transform, fit)
    result = quantize_to_bw_palette(result) if panel_type == "bw" else quantize_to_epaper_palette(result)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
