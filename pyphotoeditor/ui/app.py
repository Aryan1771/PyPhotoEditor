"""
app
===
`App` is the composition root: it creates the Document, builds every UI
region by calling the other `ui` modules, and exposes the small set of
methods (open_image, grayscale, undo, ...) that those modules bind their
buttons/menu items to. `App` never contains a filter's *algorithm* --
those all live in `core` -- it only forwards to `core` and re-renders.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

from ..core import Document, image_ops, filters, dithering, segmentation
from . import menu_bar, toolbar, tool_strip, tool_panel, dialogs
from .canvas_view import CanvasView
from .tools import TOOL_CLASSES


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PyPhotoEditor — Python Image Editor")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#202020")

        self.document = Document()
        self.brush_size = 20
        self.brush_color = (0, 0, 0, 255)
        self.tools = {name: cls() for name, cls in TOOL_CLASSES.items()}
        self.active_tool = self.tools["brush"]

        self._build_layout()
        self._bind_shortcuts()

    # ---- layout construction -----------------------------------------
    def _build_layout(self):
        menu_bar.build_menu_bar(self.root, self)
        self.zoom_label = toolbar.build_toolbar(self.root, self)

        main = tk.Frame(self.root, bg="#181818")
        main.pack(fill="both", expand=True)

        tool_strip.build_tool_strip(main, self)

        center = tk.Frame(main, bg="#111111")
        center.pack(side="left", fill="both", expand=True)
        self.canvas_view = CanvasView(center, self)

        self.tool_var = tool_panel.build_tool_panel(main, self)

        self.status_var = tk.StringVar(value="Open an image to begin.")
        tk.Label(self.root, textvariable=self.status_var, bg="#292929", fg="#bbbbbb",
                 anchor="w", padx=10).pack(side="bottom", fill="x")

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_image())
        self.root.bind("<Control-s>", lambda e: self.save_image())
        self.root.bind("<Control-n>", lambda e: self.new_image())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

    # ---- small shared UI callbacks -----------------------------------
    def status(self, text: str):
        self.status_var.set(text)

    def on_zoom_changed(self, scale_fraction: float):
        self.zoom_label.config(text=f"{int(scale_fraction * 100)}%")

    def select_tool(self, name: str):
        self.active_tool = self.tools[name]
        self.tool_var.set(name.title())
        self.status(f"Tool: {name.title()}")

    def set_brush_size(self, value):
        self.brush_size = max(1, int(float(value)))

    def set_brush_color(self, rgba):
        self.brush_color = rgba

    # ---- document lifecycle -------------------------------------------
    def new_image(self):
        dialogs.ask_new_image_size(self.root, self._create_new_document)

    def _create_new_document(self, width, height):
        self.document.new(width, height)
        self.canvas_view.render()
        self.status("New document created.")

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.document.load(Image.open(path), filepath=path)
            self.canvas_view.fit_to_window()
            self.status(f"Opened {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Open error", str(exc))

    def save_image(self):
        if self.document.image is None:
            return
        if not self.document.filepath:
            return self.save_as()
        try:
            img = self.document.image
            if self.document.filepath.lower().endswith((".jpg", ".jpeg")):
                img = img.convert("RGB")
            img.save(self.document.filepath)
            self.status("Saved.")
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))

    def save_as(self):
        if self.document.image is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp"), ("TIFF", "*.tiff")],
        )
        if path:
            self.document.filepath = path
            self.save_image()

    def undo(self):
        if self.document.undo():
            self.canvas_view.render()

    def redo(self):
        if self.document.redo():
            self.canvas_view.render()

    def reset(self):
        self.document.reset_to_original()
        self.canvas_view.render()

    def fit_to_window(self):
        self.canvas_view.fit_to_window()

    # ---- image ops / filters (all just: apply + re-render) -----------
    def grayscale(self):
        self._apply(image_ops.grayscale)

    def invert(self):
        self._apply(image_ops.invert)

    def auto_contrast(self):
        self._apply(image_ops.auto_contrast)

    def flip_horizontal(self):
        self._apply(image_ops.flip_horizontal)

    def flip_vertical(self):
        self._apply(image_ops.flip_vertical)

    def rotate(self, degrees):
        self._apply(lambda img: image_ops.rotate(img, degrees))

    def resize_dialog(self):
        if self.document.image is None:
            return
        w, h = self.document.size
        dialogs.ask_resize(self.root, w, h, lambda nw, nh: self._apply(lambda img: image_ops.resize(img, nw, nh)))

    def gaussian_blur(self):
        self._apply(filters.gaussian_blur)

    def median_filter(self):
        self._apply(filters.median_filter)

    def unsharp_mask(self):
        self._apply(filters.unsharp_mask)

    def sobel_edges(self):
        self._apply(filters.sobel_edges)

    def canny_edges(self):
        self._apply(filters.canny_edges)

    def clahe(self):
        self._apply(filters.clahe)

    def denoise_tv(self):
        self._apply(filters.denoise_tv)

    def dither(self):
        self._apply(dithering.floyd_steinberg)

    def posterize(self):
        self._apply(segmentation.kmeans_posterize)

    def rotoscope(self):
        self._apply(segmentation.rotoscope)

    def _apply(self, transform):
        if self.document.image is None:
            return
        self.document.apply(transform)
        self.canvas_view.render()
