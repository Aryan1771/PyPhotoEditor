"""
tool_panel
==========
The right-hand "PROPERTIES" panel: active tool name, brush size/color
controls, and a list of quick-filter buttons. Like the other builder
modules, it only calls methods already exposed on `App`.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, colorchooser


def build_tool_panel(parent, app):
    panel = tk.Frame(parent, bg="#252525", width=260)
    panel.pack(side="right", fill="y")
    panel.pack_propagate(False)

    tk.Label(panel, text="PROPERTIES", bg="#252525", fg="white",
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

    tool_var = tk.StringVar(value="Brush")
    tk.Label(panel, textvariable=tool_var, bg="#252525", fg="#dddddd",
             font=("Segoe UI", 10)).pack(anchor="w", padx=12)

    tk.Label(panel, text="Brush size", bg="#252525", fg="#aaa").pack(anchor="w", padx=12, pady=(18, 2))
    size_var = tk.IntVar(value=app.brush_size)
    ttk.Scale(panel, from_=1, to=150, variable=size_var,
              command=lambda v: app.set_brush_size(v)).pack(fill="x", padx=12)

    tk.Label(panel, text="Brush color", bg="#252525", fg="#aaa").pack(anchor="w", padx=12, pady=(18, 2))
    color_button = tk.Button(panel, text="Choose color", bg="#444", fg="white", relief="flat")

    def choose_color():
        result = colorchooser.askcolor()
        if result[0]:
            r, g, b = map(int, result[0])
            app.set_brush_color((r, g, b, 255))
            color_button.config(bg=result[1])

    color_button.config(command=choose_color)
    color_button.pack(fill="x", padx=12)

    ttk.Separator(panel).pack(fill="x", padx=12, pady=20)

    tk.Label(panel, text="Quick Filters", bg="#252525", fg="white",
             font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=4)

    quick_filters = [
        ("Grayscale", app.grayscale), ("Gaussian Blur", app.gaussian_blur),
        ("Median", app.median_filter), ("Sobel", app.sobel_edges),
        ("Canny", app.canny_edges), ("Dither", app.dither),
        ("K-Means", app.posterize), ("Rotoscope", app.rotoscope),
    ]
    for text, cmd in quick_filters:
        tk.Button(panel, text=text, command=cmd, bg="#343434", fg="white",
                  relief="flat", anchor="w").pack(fill="x", padx=12, pady=2)

    return tool_var
