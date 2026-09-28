"""
dialogs
=======
Small modal Toplevel dialogs. Each function takes the parent window and a
callback that receives the collected values, so this module has zero
knowledge of `Document` or `App` -- it only ever hands plain numbers back
to whoever asked for them (loose coupling: dialogs are reusable prompts).
"""

from __future__ import annotations
import tkinter as tk
from . import theme as T


def ask_new_image_size(parent, on_create):
    dialog = tk.Toplevel(parent)
    dialog.title("New Image")
    dialog.transient(parent)
    dialog.grab_set()

    width_var = tk.IntVar(value=T.DEFAULT_IMAGE[0])
    height_var = tk.IntVar(value=T.DEFAULT_IMAGE[1])
    for label, var in [("Width", width_var), ("Height", height_var)]:
        tk.Label(dialog, text=label).pack(anchor="w", padx=T.PAD, pady=(T.PAD, T.SMALL))
        tk.Entry(dialog, textvariable=var).pack(padx=T.PAD)

    def create():
        on_create(width_var.get(), height_var.get())
        dialog.destroy()

    tk.Button(dialog, text="Create", command=create).pack(pady=T.PAD)


def ask_resize(parent, current_width, current_height, on_resize):
    dialog = tk.Toplevel(parent)
    dialog.title("Resize")
    dialog.transient(parent)
    dialog.grab_set()

    width_var = tk.IntVar(value=current_width)
    height_var = tk.IntVar(value=current_height)
    lock_var = tk.BooleanVar(value=True)
    ratio = current_height / current_width if current_width else 1.0

    for label, var in [("Width", width_var), ("Height", height_var)]:
        tk.Label(dialog, text=label).pack(anchor="w", padx=T.PAD, pady=(T.PAD, T.SMALL))
        tk.Entry(dialog, textvariable=var).pack(padx=T.PAD)
    tk.Checkbutton(dialog, text="Maintain aspect ratio", variable=lock_var).pack(pady=T.GAP)

    def resize():
        new_w = max(1, width_var.get())
        new_h = max(1, int(new_w * ratio)) if lock_var.get() else max(1, height_var.get())
        on_resize(new_w, new_h)
        dialog.destroy()

    tk.Button(dialog, text="Resize", command=resize).pack(pady=T.PAD)
