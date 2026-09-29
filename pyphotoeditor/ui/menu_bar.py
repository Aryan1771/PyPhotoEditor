"""
menu_bar
========
Builds the top menu bar. This module only wires menu labels to methods
already exposed on `App` -- it contains no image-processing or drawing
logic itself, so the menu structure can be edited freely without touching
how any command actually works.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from . import theme as T
from .widgets import RoundedButton


def build_menu_bar(root, app):
    menu = tk.Frame(root, bg=T.BG_SIDEBAR)
    menu.pack(fill="x")
    def cascade(label, menu):
        button = RoundedButton(bar, text=label, width=T.SLIDER_WIDTH)
        button.command = lambda: menu.tk_popup(button.winfo_rootx(), button.winfo_rooty()+button.winfo_height())
        button.pack(side="left", padx=T.BORDER_WIDTH, pady=T.SMALL)
    bar = menu

    file_m = tk.Menu(menu, tearoff=False)
    file_m.add_command(label="New", command=app.new_image, accelerator="Ctrl+N")
    file_m.add_command(label="Open…", command=app.open_image, accelerator="Ctrl+O")
    file_m.add_command(label="Save", command=app.save_image, accelerator="Ctrl+S")
    file_m.add_command(label="Save As…", command=app.save_as)
    file_m.add_separator()
    file_m.add_command(label="Exit", command=app.close)
    cascade(label="File", menu=file_m)

    edit_m = tk.Menu(menu, tearoff=False)
    edit_m.add_command(label="Undo", command=app.undo, accelerator="Ctrl+Z")
    edit_m.add_command(label="Redo", command=app.redo, accelerator="Ctrl+Y")
    edit_m.add_separator()
    edit_m.add_command(label="Reset to Original", command=app.reset)
    cascade(label="Edit", menu=edit_m)

    image_m = tk.Menu(menu, tearoff=False)
    image_m.add_command(label="Grayscale", command=app.grayscale)
    image_m.add_command(label="Invert", command=app.invert)
    image_m.add_command(label="Auto Contrast", command=app.auto_contrast)
    image_m.add_command(label="Resize…", command=app.resize_dialog)
    image_m.add_command(label="Rotate 90°", command=lambda: app.rotate(90))
    image_m.add_command(label="Rotate -90°", command=lambda: app.rotate(-90))
    image_m.add_command(label="Flip Horizontal", command=app.flip_horizontal)
    image_m.add_command(label="Flip Vertical", command=app.flip_vertical)
    cascade(label="Image", menu=image_m)

    filters_m = tk.Menu(menu, tearoff=False)
    filters_m.add_command(label="Gaussian Blur", command=app.gaussian_blur)
    filters_m.add_command(label="Median Filter", command=app.median_filter)
    filters_m.add_command(label="Unsharp Mask", command=app.unsharp_mask)
    filters_m.add_command(label="Sobel Edges", command=app.sobel_edges)
    filters_m.add_command(label="Canny Edges", command=app.canny_edges)
    filters_m.add_command(label="CLAHE", command=app.clahe)
    filters_m.add_command(label="Denoise (TV)", command=app.denoise_tv)
    filters_m.add_separator()
    filters_m.add_command(label="Dithering", command=app.dither)
    filters_m.add_command(label="Posterize / K-Means", command=app.posterize)
    filters_m.add_command(label="Rotoscope / Foreground", command=app.rotoscope)
    cascade(label="Filters", menu=filters_m)

    help_m = tk.Menu(menu, tearoff=False)
    help_m.add_command(
        label="About",
        command=lambda: messagebox.showinfo(
            "About PyPhotoEditor",
            "PyPhotoEditor is a Photoshop-style educational image editor built with "
            "Python, Tkinter, Pillow, NumPy, SciPy, scikit-image and scikit-learn.",
        ),
    )
    cascade(label="Help", menu=help_m)
