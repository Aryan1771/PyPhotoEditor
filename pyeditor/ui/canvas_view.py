"""
canvas_view
===========
Owns the Tkinter `Canvas` widget: rendering the current image (scaled to
fit/zoom), translating screen coordinates to image-pixel coordinates, and
forwarding mouse events to whatever tool is currently active on `App`.

CanvasView never edits pixels itself -- it only reads `app.document.image`
to render, and calls `app.active_tool.on_down/on_move/on_up`. This keeps
"how do I draw a stroke" (tools.py) decoupled from "how do I show the
picture on screen" (this module).
"""

from __future__ import annotations
import tkinter as tk
from PIL import Image, ImageTk


class CanvasView:
    def __init__(self, parent, app):
        self.app = app
        self.zoom = 1.0
        self.display_size = (1, 1)
        self.image_origin = (0, 0)
        self._tk_image = None

        self.widget = tk.Canvas(parent, bg="#101010", highlightthickness=0, cursor="crosshair")
        self.widget.pack(side="left", fill="both", expand=True)

        self.widget.bind("<Configure>", lambda e: self.render())
        self.widget.bind("<ButtonPress-1>", self._on_down)
        self.widget.bind("<B1-Motion>", self._on_move)
        self.widget.bind("<ButtonRelease-1>", self._on_up)
        self.widget.bind("<MouseWheel>", self._on_wheel)
        self.widget.bind("<Button-4>", lambda e: self.zoom_by(1.1))
        self.widget.bind("<Button-5>", lambda e: self.zoom_by(1 / 1.1))

    # ---- rendering ---------------------------------------------------
    def render(self):
        self.widget.delete("all")
        doc = self.app.document
        if doc.image is None:
            cw, ch = self._canvas_size()
            self.widget.create_text(cw // 2, ch // 2, text="Open an image or create a new document",
                                     fill="#777", font=("Segoe UI", 16))
            return

        cw, ch = self._canvas_size()
        iw, ih = doc.image.size
        scale = min((cw - 30) / iw, (ch - 30) / ih) * self.zoom
        scale = max(0.05, min(scale, 8))
        self.display_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))

        preview = doc.image.resize(self.display_size, Image.Resampling.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(preview)
        self.image_origin = ((cw - self.display_size[0]) // 2, (ch - self.display_size[1]) // 2)
        self.widget.create_image(*self.image_origin, anchor="nw", image=self._tk_image)
        self.app.on_zoom_changed(scale)

    def draw_marquee(self, box):
        """Re-render then overlay a dashed selection rectangle (used by shape/crop tools)."""
        self.render()
        doc = self.app.document
        if doc.image is None:
            return
        x1, y1, x2, y2 = box
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        ox, oy = self.image_origin
        dw, dh = self.display_size
        sx, sy = dw / doc.image.width, dh / doc.image.height
        self.widget.create_rectangle(ox + x1 * sx, oy + y1 * sy, ox + x2 * sx, oy + y2 * sy,
                                      outline="white", dash=(5, 3), width=2)

    def fit_to_window(self):
        self.zoom = 1.0
        self.render()

    def zoom_by(self, factor):
        if self.app.document.image is None:
            return
        self.zoom = max(0.1, min(6.0, self.zoom * factor))
        self.render()

    # ---- coordinate mapping -------------------------------------------
    def _canvas_size(self):
        return max(1, self.widget.winfo_width()), max(1, self.widget.winfo_height())

    def to_image_point(self, x, y):
        doc = self.app.document
        if doc.image is None:
            return None
        ox, oy = self.image_origin
        dw, dh = self.display_size
        if not (ox <= x < ox + dw and oy <= y < oy + dh):
            return None
        ix = int((x - ox) * doc.image.width / dw)
        iy = int((y - oy) * doc.image.height / dh)
        return max(0, min(doc.image.width - 1, ix)), max(0, min(doc.image.height - 1, iy))

    # ---- event routing to the active tool -------------------------------
    def _on_down(self, event):
        p = self.to_image_point(event.x, event.y)
        if p:
            self.app.active_tool.on_down(self.app, p)
            self.render()

    def _on_move(self, event):
        p = self.to_image_point(event.x, event.y)
        if p:
            self.app.active_tool.on_move(self.app, p)
            if self.app.active_tool.name in ("brush", "pencil", "eraser"):
                self.render()

    def _on_up(self, event):
        p = self.to_image_point(event.x, event.y) or (0, 0)
        self.app.active_tool.on_up(self.app, p)
        self.render()

    def _on_wheel(self, event):
        self.zoom_by(1.1 if event.delta > 0 else 1 / 1.1)
