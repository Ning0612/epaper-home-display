from __future__ import annotations

import math
from collections import deque

from PIL import Image, ImageChops

# 40px keeps the tile grid small (20x12 for an 800x480 panel) while staying a
# multiple of 8 so aligned regions never need to grow past a tile boundary.
TILE_SIZE = 40
# More disjoint regions than this means the per-region init_part()+busy-wait
# overhead would likely exceed the cost of one larger rectangle.
MAX_REGIONS = 6


def _align_box(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    xs = max(0, (left // 8) * 8)
    xe = min(width, ((right + 7) // 8) * 8)
    ys = max(0, top)
    ye = min(height, bottom)
    return (xs, ys, xe, ye)


def pack_mono_buffer(image: Image.Image) -> bytearray:
    # Matches EPD.getbuffer()'s inversion exactly (same convert("1") + XOR
    # 0xFF). A theoretical trace through epd7in5_V2.display_Partial()'s
    # internal `~Image[...]` suggested this should NOT be inverted here, but
    # real epd7in5_V2 hardware showed the opposite: without this XOR, the
    # partially-refreshed region rendered with black/white flipped relative
    # to a full refresh of the same content. Partial mode's 0x13 register
    # apparently doesn't share full-refresh mode's polarity, despite what the
    # driver source alone implies — trust the hardware result, not the trace.
    img = image.convert("1")
    buf = bytearray(img.tobytes("raw"))
    for i in range(len(buf)):
        buf[i] ^= 0xFF
    return buf


def _connected_components(dirty: list[list[bool]], rows: int, cols: int) -> list[list[tuple[int, int]]]:
    visited = [[False] * cols for _ in range(rows)]
    components: list[list[tuple[int, int]]] = []
    for ty in range(rows):
        for tx in range(cols):
            if not dirty[ty][tx] or visited[ty][tx]:
                continue
            component: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(tx, ty)])
            visited[ty][tx] = True
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < cols and 0 <= ny < rows and dirty[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
            components.append(component)
    return components


def compute_dirty_regions(
    prev: Image.Image | None,
    curr: Image.Image,
    tile_size: int = TILE_SIZE,
    max_regions: int = MAX_REGIONS,
) -> list[tuple[int, int, int, int]] | None:
    """Diff prev/curr and return disjoint changed rectangles, or None if no baseline exists."""
    if prev is None or prev.size != curr.size:
        return None

    diff = ImageChops.difference(prev.convert("RGB"), curr.convert("RGB"))
    overall_bbox = diff.getbbox()
    if overall_bbox is None:
        return []

    width, height = curr.size
    # _align_box() rounds Xend up to a multiple of 8 and clamps it to width;
    # that only stays a multiple of 8 if width itself is one (true for every
    # panel this project targets, 800px wide).
    assert width % 8 == 0, "compute_dirty_regions requires an 8-aligned image width"
    cols = math.ceil(width / tile_size)
    rows = math.ceil(height / tile_size)

    dirty = [[False] * cols for _ in range(rows)]
    for ty in range(rows):
        y0 = ty * tile_size
        y1 = min(y0 + tile_size, height)
        for tx in range(cols):
            x0 = tx * tile_size
            x1 = min(x0 + tile_size, width)
            dirty[ty][tx] = diff.crop((x0, y0, x1, y1)).getbbox() is not None

    components = _connected_components(dirty, rows, cols)

    if len(components) > max_regions:
        return [_align_box(overall_bbox, width, height)]

    regions: list[tuple[int, int, int, int]] = []
    for component in components:
        tile_xs = [tx for tx, _ in component]
        tile_ys = [ty for _, ty in component]
        min_tx, max_tx = min(tile_xs), max(tile_xs)
        min_ty, max_ty = min(tile_ys), max(tile_ys)

        px_left = min_tx * tile_size
        px_right = min((max_tx + 1) * tile_size, width)
        px_top = min_ty * tile_size
        px_bottom = min((max_ty + 1) * tile_size, height)

        # Guaranteed non-None: every tile in this component was marked dirty
        # by at least one changed pixel within its own bounds.
        crop_l, t, r, b = diff.crop((px_left, px_top, px_right, px_bottom)).getbbox()
        abs_box = (crop_l + px_left, t + px_top, r + px_left, b + px_top)
        regions.append(_align_box(abs_box, width, height))

    regions.sort(key=lambda box: (box[1], box[0]))
    return regions
