import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EXTENSION_NAME = "ruminar.ephemeral_preview_tap";
const EVENT_NAME = "ruminar.ephemeral_preview";
const TARGET_CLASS = "EphemeralPreviewTap";

const MIN_NODE_WIDTH = 280;
const MIN_NODE_HEIGHT = 360;
const PREVIEW_MARGIN = 8;
const PREVIEW_MAX_HEIGHT = 1600;
const CAPTION_HEIGHT = 18;

function ensureNodeSize(node) {
    if (!node.size) return;
    node.size[0] = Math.max(node.size[0], MIN_NODE_WIDTH);
    node.size[1] = Math.max(node.size[1], MIN_NODE_HEIGHT);
}

function drawPreview(node, ctx) {
    const img = node.__ephemeralPreviewImage;
    if (!img || node.flags?.collapsed) return;

    const availableWidth = Math.max(1, node.size[0] - PREVIEW_MARGIN * 2);
    const availableHeight = Math.max(1, node.size[1] - PREVIEW_MARGIN * 2 - CAPTION_HEIGHT);

    let drawWidth = availableWidth;
    let drawHeight = drawWidth * (img.height / img.width);

    if (drawHeight > availableHeight) {
        drawHeight = availableHeight;
        drawWidth = drawHeight * (img.width / img.height);
    }

    if (drawHeight > PREVIEW_MAX_HEIGHT) {
        drawHeight = PREVIEW_MAX_HEIGHT;
        drawWidth = drawHeight * (img.width / img.height);
    }

    // If width grew because of PREVIEW_MAX_HEIGHT limiting, clamp again.
    if (drawWidth > availableWidth) {
        drawWidth = availableWidth;
        drawHeight = drawWidth * (img.height / img.width);
    }

    const x = PREVIEW_MARGIN + (availableWidth - drawWidth) / 2;
    const y = node.size[1] - PREVIEW_MARGIN - drawHeight;

    ctx.save();

    ctx.fillStyle = "rgba(0, 0, 0, 0.20)";
    ctx.fillRect(
        PREVIEW_MARGIN,
        y - CAPTION_HEIGHT,
        availableWidth,
        drawHeight + CAPTION_HEIGHT
    );

    const meta = node.__ephemeralPreviewMeta;
    if (meta) {
        ctx.fillStyle = "#DDDDDD";
        ctx.font = "12px sans-serif";
        const label = `${meta.count} img · ${meta.columns}×${meta.rows} · sheet ${meta.width}×${meta.height}`;
        ctx.fillText(label, PREVIEW_MARGIN + 6, y - 5);
    }

    ctx.drawImage(img, x, y, drawWidth, drawHeight);
    ctx.restore();
}

api.addEventListener(EVENT_NAME, ({ detail }) => {
    const nodeId = Number(detail.node);
    if (!Number.isFinite(nodeId)) return;

    const node = app.graph?.getNodeById(nodeId);
    if (!node) return;

    const dataUrl = `data:image/${detail.format};base64,${detail.image}`;
    const img = new Image();

    img.onload = () => {
        node.__ephemeralPreviewImage = img;
        node.__ephemeralPreviewMeta = {
            width: detail.width,
            height: detail.height,
            count: detail.count ?? 1,
            columns: detail.columns ?? 1,
            rows: detail.rows ?? 1,
            tile_width: detail.tile_width,
            tile_height: detail.tile_height,
        };
        ensureNodeSize(node);
        app.graph.setDirtyCanvas(true, true);
    };

    img.src = dataUrl;
});

app.registerExtension({
    name: EXTENSION_NAME,

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET_CLASS) return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;
            ensureNodeSize(this);
            return result;
        };

        const origOnDrawBackground = nodeType.prototype.onDrawBackground;
        nodeType.prototype.onDrawBackground = function (ctx) {
            if (origOnDrawBackground) {
                origOnDrawBackground.apply(this, arguments);
            }
            drawPreview(this, ctx);
        };
    },
});
