"""
tools
=====
Each drawing tool is a small class implementing the same interface:

    on_down(app, point)
    on_move(app, point)
    on_up(app, point)

`point` is an (x, y) pixel coordinate already mapped into image space by
CanvasView. Tools mutate `app.document.image` directly via Pillow's
ImageDraw and call `app.document.push_undo()` themselves at the start of a
stroke/shape, so `CanvasView` doesn't need to know anything about *how*
any particular tool works -- it just forwards events to `app.active_tool`.
This keeps adding a new tool to a single new class + one registry entry.
"""

from __future__ import annotations
from PIL import ImageDraw, Image
import numpy as np


class BaseTool:
    name = "base"

    def on_down(self, app, point):
        pass

    def on_move(self, app, point):
        pass

    def on_up(self, app, point):
        pass


class _FreehandTool(BaseTool):
    """Shared behavior for brush/pencil/eraser (all are 'drag to paint')."""

    def __init__(self):
        self._last = None

    def on_down(self, app, point):
        doc = app.document
        if doc.image is None:
            return
        doc.push_undo()
        self._last = point
        self._paint(app, point, point)

    def on_move(self, app, point):
        if self._last is None:
            return
        self._paint(app, self._last, point)
        self._last = point

    def on_up(self, app, point):
        self._last = None

    def _paint(self, app, p1, p2):
        raise NotImplementedError


class BrushTool(_FreehandTool):
    name = "brush"

    def _paint(self, app, p1, p2):
        img = app.document.image
        draw = ImageDraw.Draw(img)
        width = app.brush_size
        draw.line([p1, p2], fill=app.brush_color, width=width)
        r = width // 2
        draw.ellipse((p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r), fill=app.brush_color)


class PencilTool(_FreehandTool):
    name = "pencil"

    def _paint(self, app, p1, p2):
        draw = ImageDraw.Draw(app.document.image)
        draw.line([p1, p2], fill=app.brush_color, width=2)


class EraserTool(_FreehandTool):
    name = "eraser"

    def _paint(self, app, p1, p2):
        img = app.document.image
        width = app.brush_size
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).line([p1, p2], fill=255, width=width)
        alpha = np.asarray(img.getchannel("A"))
        new_alpha = np.where(np.asarray(mask) > 0, 0, alpha).astype(np.uint8)
        img.putalpha(Image.fromarray(new_alpha))


class _ShapeTool(BaseTool):
    """Shared behavior for rectangle/ellipse: drag out a bounding box."""

    def __init__(self):
        self.box = None

    def on_down(self, app, point):
        self.box = [point[0], point[1], point[0], point[1]]

    def on_move(self, app, point):
        if self.box:
            self.box[2:] = [point[0], point[1]]
            app.canvas_view.draw_marquee(self.box)

    def on_up(self, app, point):
        if not self.box:
            return
        x1, y1, x2, y2 = self._normalized()
        if x2 > x1 and y2 > y1:
            app.document.push_undo()
            self._commit(app, (x1, y1, x2, y2))
        self.box = None

    def _normalized(self):
        x1, y1, x2, y2 = self.box
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def _commit(self, app, box):
        raise NotImplementedError


class RectangleTool(_ShapeTool):
    name = "rect"

    def _commit(self, app, box):
        draw = ImageDraw.Draw(app.document.image)
        draw.rectangle(box, outline=app.brush_color, width=max(1, app.brush_size // 4))


class EllipseTool(_ShapeTool):
    name = "ellipse"

    def _commit(self, app, box):
        draw = ImageDraw.Draw(app.document.image)
        draw.ellipse(box, outline=app.brush_color, width=max(1, app.brush_size // 4))


class CropTool(_ShapeTool):
    name = "crop"

    def _commit(self, app, box):
        app.document.image = app.document.image.crop(box)


class EyedropperTool(BaseTool):
    name = "eyedropper"

    def on_down(self, app, point):
        if app.document.image is None:
            return
        app.set_brush_color(app.document.image.getpixel(point))


# Registry: single source of truth for "which tools exist" used by both
# the toolbar (to build buttons) and App (to instantiate/select tools).
TOOL_CLASSES = {
    "brush": BrushTool,
    "pencil": PencilTool,
    "eraser": EraserTool,
    "rect": RectangleTool,
    "ellipse": EllipseTool,
    "crop": CropTool,
    "eyedropper": EyedropperTool,
}
