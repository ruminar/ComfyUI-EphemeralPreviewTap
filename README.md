# Ephemeral Preview Tap

A lightweight ComfyUI custom node that previews incoming `IMAGE` batches as a temporary contact sheet.

## Features

- Accepts `IMAGE` and passes it through unchanged.
- Builds a contact sheet from the current batch.
- Sends the preview only to the current executing client.
- Does **not** save anything to ComfyUI temp/output folders.
- Uses fixed settings for simplicity:
  - JPEG quality: **82**
  - Gap: **6**
  - Max images: **64**
  - Tile size: **half of each source image**
  - Grid layout: chosen automatically to approach a square, using tile aspect ratio.

## Installation

Copy this folder into your `ComfyUI/custom_nodes/` directory and restart ComfyUI.

## Usage

Place the node inline where you want to inspect the image stream:

```text
KSampler
  ↓
VAE Decode
  ↓
Ephemeral Preview Tap
  ↓
Face Fix / Hand Fix / Upscale / Save
```

The node previews the image batch while passing the original `IMAGE` downstream unchanged.

## Notes

- The preview is ephemeral: it updates when images pass through the node and is not restored after page reload.
- For large batches, only the first **64** images are shown.
- The preview image is scaled in the node UI to fit the node width, with a large height cap for zoomed inspection.
