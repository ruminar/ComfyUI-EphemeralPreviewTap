from .ephemeral_preview_tap import EphemeralPreviewTap

NODE_CLASS_MAPPINGS = {
    "EphemeralPreviewTap": EphemeralPreviewTap,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EphemeralPreviewTap": "Ephemeral Preview Tap",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
