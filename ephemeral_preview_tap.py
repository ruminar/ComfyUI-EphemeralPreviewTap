import base64
import io
import logging
import math

import numpy as np
from PIL import Image

from server import PromptServer

logger = logging.getLogger(__name__)
EVENT_NAME = "ruminar.ephemeral_preview"
JPEG_QUALITY = 80
JPEG_OPTIMIZE = False
GAP = 6
MAX_IMAGES = 64
TILE_SCALE = 0.5
MAX_TILE_LONG_SIDE = 512


def _to_numpy_batch(image_tensor):
    if image_tensor.ndim == 3:
        image_tensor = image_tensor.unsqueeze(0)
    return image_tensor.detach().cpu().numpy()


def _array_to_pil(arr):
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)

    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")

    channels = arr.shape[-1]
    if channels == 1:
        return Image.fromarray(arr[..., 0], mode="L")
    if channels == 3:
        return Image.fromarray(arr, mode="RGB")
    if channels == 4:
        return Image.fromarray(arr, mode="RGBA")

    raise ValueError(f"Unsupported channel count for preview: {channels}")


def _thumbnail_preview_size(pil_image):
    target_width = max(1, int(pil_image.width * TILE_SCALE))
    target_height = max(1, int(pil_image.height * TILE_SCALE))

    long_side = max(target_width, target_height)
    if long_side > MAX_TILE_LONG_SIDE:
        scale = MAX_TILE_LONG_SIDE / long_side
        target_width = max(1, int(target_width * scale))
        target_height = max(1, int(target_height * scale))

    thumb = pil_image.copy()
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    thumb.thumbnail((target_width, target_height), resampling)
    return thumb


def _compute_grid(count, tile_width, tile_height):
    # Choose columns so the final sheet approaches a square,
    # taking tile aspect ratio into account.
    cols = max(1, math.ceil(math.sqrt(count * (tile_height / tile_width))))
    rows = math.ceil(count / cols)
    return cols, rows


def _build_contact_sheet(images, gap=GAP):
    if not images:
        raise ValueError("No images to preview")

    count = len(images)
    max_tile_width = max(img.width for img in images)
    max_tile_height = max(img.height for img in images)
    cols, rows = _compute_grid(count, max_tile_width, max_tile_height)

    sheet_width = cols * max_tile_width + (cols + 1) * gap
    sheet_height = rows * max_tile_height + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_width, sheet_height), (24, 24, 24))

    for idx, img in enumerate(images):
        row = idx // cols
        col = idx % cols

        x0 = gap + col * (max_tile_width + gap)
        y0 = gap + row * (max_tile_height + gap)

        paste_x = x0 + (max_tile_width - img.width) // 2
        paste_y = y0 + (max_tile_height - img.height) // 2

        if img.mode == "RGBA":
            sheet.paste(img, (paste_x, paste_y), img)
        else:
            sheet.paste(img, (paste_x, paste_y))

    return sheet, cols, rows, max_tile_width, max_tile_height


def _encode_jpeg(pil_image, quality=JPEG_QUALITY):
    if pil_image.mode not in ("RGB", "L"):
        pil_image = pil_image.convert("RGB")

    buffer = io.BytesIO()
    pil_image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=False,
    )
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class EphemeralPreviewTap:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "tap"
    CATEGORY = "image/utils"

    @classmethod
    def IS_CHANGED(cls, image, unique_id=None):
        return float("nan")

    def tap(self, image, unique_id=None):
        try:
            batch = _to_numpy_batch(image)
            pil_images = [_array_to_pil(arr) for arr in batch[:MAX_IMAGES]]
            thumbs = [_thumbnail_preview_size(img) for img in pil_images]
            sheet, cols, rows, tile_width, tile_height = _build_contact_sheet(thumbs, gap=GAP)
            encoded = _encode_jpeg(sheet, quality=JPEG_QUALITY)

            payload = {
                "node": int(unique_id) if unique_id is not None else None,
                "image": encoded,
                "format": "jpeg",
                "width": sheet.width,
                "height": sheet.height,
                "count": len(thumbs),
                "columns": cols,
                "rows": rows,
                "tile_width": tile_width,
                "tile_height": tile_height,
                "gap": GAP,
                "max_images": MAX_IMAGES,
                "quality": JPEG_QUALITY,
            }

            server = PromptServer.instance
            client_id = getattr(server, "client_id", None)
            if client_id:
                server.send_sync(EVENT_NAME, payload, client_id)
            else:
                server.send_sync(EVENT_NAME, payload)

        except Exception:
            logger.exception("Ephemeral Preview Tap failed to generate/send preview.")

        return (image,)
