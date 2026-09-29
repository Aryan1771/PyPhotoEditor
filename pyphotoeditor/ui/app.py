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
from ..core.export import save_image as export_image
from ..core.image_io import load_image, SUPPORTED_EXTENSIONS
from . import menu_bar, toolbar, tool_strip, tool_panel, dialogs
from . import theme as T
from .canvas_view import CanvasView
from .tools import TOOL_CLASSES
from .tool_options import build_options
from .worker import OperationRunner


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        T.install(root)
        self.root.title("PyPhotoEditor — Python Image Editor")
        self.root.geometry(T.WINDOW_SIZE)
        self.root.minsize(*T.MIN_WINDOW)
        self.root.configure(bg=T.BG_APP)

        self.document = Document()
        self.source_path = None
        self.busy = False
        self.drawing = False
        self.runner = OperationRunner(self)
        self.brush_shape = "circle"
        self.brush_strength = 100
        self.brush_hardness = 100
        self.stroke_mode = "Once per stroke"
        self.effect_params = {}
        self.brush_size = T.DEFAULT_BRUSH
        self.brush_color = T.DEFAULT_COLOR
        self.tools = {name: cls() for name, cls in TOOL_CLASSES.items()}
        self.active_tool = self.tools["brush"]

        self._build_layout()
        build_options(self)
        self._bind_shortcuts()
        self.history_list.bind("<<ListboxSelect>>", self._history_jump)
        self.refresh_history()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ---- layout construction -----------------------------------------
    def _build_layout(self):
        menu_bar.build_menu_bar(self.root, self)
        self.zoom_label = toolbar.build_toolbar(self.root, self)
        self.options = tk.Frame(self.root, bg=T.BG_APP)
        self.options.pack(fill="x")
        tk.Label(self.options, text="Brush options • choose a tool on the left", fg=T.TEXT_MUTED).pack(anchor="w", padx=T.PAD, pady=T.GAP)

        main = tk.Frame(self.root, bg=T.BG_APP)
        main.pack(fill="both", expand=True)

        tool_strip.build_tool_strip(main, self)

        center = tk.Frame(main, bg=T.WORKSPACE)
        center.pack(side="left", fill="both", expand=True)
        self.canvas_view = CanvasView(center, self)

        self.tool_var = tool_panel.build_tool_panel(main, self)

        self.status_var = tk.StringVar(value="Open an image to begin.")
        tk.Label(self.root, textvariable=self.status_var, bg=T.BG_SURFACE, fg=T.TEXT_MUTED,
                 anchor="w", padx=T.PAD).pack(side="bottom", fill="x")

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_image())
        self.root.bind("<Control-s>", lambda e: self.save_image())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind("<Control-n>", lambda e: self.new_image())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<bracketleft>", lambda e: self.adjust_size(-5))
        self.root.bind("<bracketright>", lambda e: self.adjust_size(5))

    # ---- small shared UI callbacks -----------------------------------
    def status(self, text: str):
        self.status_var.set(text)

    def on_zoom_changed(self, scale_fraction: float):
        self.zoom_label.config(text=f"{int(scale_fraction * 100)}%")

    def select_tool(self, name: str):
        self.active_tool.on_up(self, None)
        self.active_tool = self.tools[name]
        build_options(self)
        self.tool_var.set(getattr(self.active_tool,"label",name.title()))
        self.status(f"Tool: {self.tool_var.get()}")
        for key, button in self.tool_buttons.items():
            button.set_selected(key == name)

    def refresh_history(self):
        self.document.finish_pending()
        self.update_title()
        self.history_list.delete(0, "end")
        self.history_list.insert("end", "Initial / retained state")
        for command in self.document.history:
            self.history_list.insert("end", command.name)
        self.history_list.selection_set(self.document.history_index)
        if "restore" in self.tool_buttons:
            self.tool_buttons["restore"].set_disabled(not self.document.can_restore)

    def update_title(self):
        path = self.document.filepath or self.source_path
        name = os.path.basename(path) if path else "Untitled"
        marker = "* " if self.document.dirty else ""
        self.root.title(f"{marker}{name} — PyPhotoEditor")

    def confirm_replace(self):
        if not self.document.dirty:
            return True
        answer = messagebox.askyesnocancel("Unsaved changes", "Save your changes before continuing?", parent=self.root)
        if answer is None:
            return False
        return bool(self.save_image()) if answer else True

    def close(self):
        if not self.confirm_replace():
            return
        self.runner.shutdown()
        self.root.destroy()

    def _history_jump(self, event):
        selected = self.history_list.curselection()
        if selected:
            self.document.jump_to(selected[0])
            self.update_title()
            self.canvas_view.render()
            self.tool_buttons["restore"].set_disabled(not self.document.can_restore)

    def toggle_panel(self):
        if self.right_panel.winfo_manager():
            self.right_panel.pack_forget()
        else:
            self.right_panel.pack(side="right", fill="y")

    def adjust_size(self, delta):
        if self.root.focus_get() and self.root.focus_get().winfo_class() in ("Entry", "TEntry"):
            return
        self.set_brush_size(self.brush_size + delta)
        if hasattr(self, "size_var"):
            self.size_var.set(self.brush_size)

    def set_brush_size(self, value):
        self.brush_size = max(1, min(500, int(float(value))))

    def set_brush_color(self, rgba):
        self.brush_color = rgba

    # ---- document lifecycle -------------------------------------------
    def new_image(self):
        if not self.confirm_replace():
            return
        dialogs.ask_new_image_size(self.root, self._create_new_document)

    def _create_new_document(self, width, height):
        self.document.new(width, height)
        self.source_path = None
        self.update_title()
        self.refresh_history()
        self.canvas_view.render()
        self.status("New document created.")

    def open_image(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                parent=self.root,
                title="Open image in PyPhotoEditor",
                filetypes=[("Images", " ".join("*"+ext for ext in SUPPORTED_EXTENSIONS)), ("All files", "*.*")],
            )
        if not path:
            return False
        try:
            loaded = load_image(path)
            if not self.confirm_replace():
                return False
            self.document.load(loaded.image, filepath=loaded.save_path)
            self.source_path = loaded.source
            self.refresh_history()
            self.canvas_view.fit_to_window()
            self.root.title(f"{os.path.basename(path)} — PyPhotoEditor")
            detail = f"; editing first of {loaded.frames} frames/pages" if loaded.frames > 1 else ""
            self.status(f"Opened {os.path.basename(path)} ({loaded.format}){detail}")
            return True
        except Exception as exc:
            messagebox.showerror("Open error", f"Could not open this image.\n\n{exc}", parent=self.root)
            return False

    def save_image(self):
        if self.document.image is None:
            return False
        if not self.document.filepath:
            return self.save_as()
        return self._save_to(self.document.filepath)

    def _save_to(self, path):
        if self.document.image is None:
            return False
        try:
            if str(path).lower().endswith((".jpg", ".jpeg")):
                if not messagebox.askokcancel("JPEG transparency", "JPEG cannot preserve transparency. Save flattened onto white?", parent=self.root):
                    return False
            export_image(self.document.image, path)
            self.document.filepath = os.path.abspath(path)
            self.source_path = self.document.filepath
            self.document.mark_saved()
            self.update_title()
            self.status("Saved.")
            return True
        except Exception as exc:
            messagebox.showerror("Save error", str(exc), parent=self.root)
            return False

    def save_as(self):
        if self.document.image is None:
            return False
        path = filedialog.asksaveasfilename(
            parent=self.root,
            initialfile=os.path.splitext(os.path.basename(self.source_path))[0]+".png" if self.source_path else "Untitled.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp"), ("TIFF", "*.tiff")],
        )
        return self._save_to(path) if path else False

    def undo(self):
        self.active_tool.on_up(self, None)
        if self.document.undo():
            self.refresh_history()
            self.canvas_view.render()

    def redo(self):
        self.active_tool.on_up(self, None)
        if self.document.redo():
            self.refresh_history()
            self.canvas_view.render()

    def reset(self):
        self.active_tool.on_up(self, None)
        self.document.reset_to_original()
        self.refresh_history()
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
        self._apply(lambda img: image_ops.rotate(img, degrees), f"Rotate {degrees}°")

    def resize_dialog(self):
        if self.document.image is None:
            return
        w, h = self.document.size
        dialogs.ask_resize(self.root, w, h, lambda nw, nh: self._apply(lambda img: image_ops.resize(img, nw, nh), "Resize"))

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

    def _apply(self, transform, name=None):
        if self.document.image is None:
            return
        name = name or getattr(transform, "__name__", "Image operation").replace("_", " ").title()
        self.runner.start(transform, name)


def _after_stroke(method):
    """Serialize document commands behind any queued pointer samples."""
    from functools import wraps
    @wraps(method)
    def call(self,*args,**kwargs):
        if self.drawing:
            self.active_tool.on_up(self,None)
            self.root.after(T.POLL_MS,lambda:call(self,*args,**kwargs))
            return
        return method(self,*args,**kwargs)
    return call


for _method in ('close','select_tool','new_image','_create_new_document','open_image','save_image','save_as','undo','redo','reset','_apply','_history_jump'):
    setattr(App,_method,_after_stroke(getattr(App,_method)))
