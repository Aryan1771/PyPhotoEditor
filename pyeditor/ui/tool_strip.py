"""
tool_strip
==========
The narrow left-hand strip of tool-selection buttons (brush, pencil,
eraser, ...). Reads its list of tools from `tools.TOOL_CLASSES` so adding
a new tool there automatically gives it a button here too.
"""

from __future__ import annotations
import tkinter as tk

TOOL_ICONS = {
    "brush": ("🖌", "Brush"),
    "pencil": ("✏", "Pencil"),
    "eraser": ("⌫", "Eraser"),
    "rect": ("▣", "Rectangle"),
    "ellipse": ("○", "Ellipse"),
    "crop": ("⊞", "Crop"),
    "eyedropper": ("I", "Eyedropper"),
}


def build_tool_strip(parent, app):
    strip = tk.Frame(parent, bg="#252525", width=70)
    strip.pack(side="left", fill="y")
    strip.pack_propagate(False)

    for name, (icon, tip) in TOOL_ICONS.items():
        button = tk.Button(strip, text=icon, command=lambda n=name: app.select_tool(n),
                            bg="#303030", fg="white", activebackground="#555",
                            relief="flat", font=("Segoe UI Symbol", 16), width=4)
        button.pack(pady=5, padx=6)
        button.bind("<Enter>", lambda e, t=tip: app.status(t))
    return strip
