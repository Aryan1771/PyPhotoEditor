"""
toolbar
=======
The horizontal quick-action strip under the menu bar (Open/Save/Undo/Redo/
Fit + zoom readout). Like menu_bar.py, this only wires buttons to methods
already on `App`.
"""

from __future__ import annotations
import tkinter as tk


def build_toolbar(parent, app):
    top = tk.Frame(parent, bg="#292929", height=44)
    top.pack(side="top", fill="x")

    actions = [
        ("Open", app.open_image),
        ("Save", app.save_image),
        ("Undo", app.undo),
        ("Redo", app.redo),
        ("Fit", app.fit_to_window),
    ]
    for text, cmd in actions:
        tk.Button(top, text=text, command=cmd, bg="#3a3a3a", fg="white",
                  activebackground="#505050", activeforeground="white",
                  relief="flat", padx=12).pack(side="left", padx=3, pady=7)

    zoom_label = tk.Label(top, text="100%", bg="#292929", fg="white")
    zoom_label.pack(side="right", padx=12)
    return zoom_label
