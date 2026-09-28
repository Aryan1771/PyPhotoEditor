"""
main
====
The single entry point. Kept to a few lines on purpose: it just creates
the Tk root, sets the window icon from assets/logo, and hands control to
`App`. Nothing else in the codebase imports this module, so `core` and
`ui` remain independently importable/testable.
"""

from __future__ import annotations
import os
import tkinter as tk

from .ui.app import App

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


def _set_icon(root: tk.Tk) -> None:
    """Best-effort window icon from the PNG rendering of the SVG logo."""
    png_path = os.path.join(ASSETS_DIR, "logo.png")
    if os.path.exists(png_path):
        try:
            icon = tk.PhotoImage(file=png_path)
            root.iconphoto(True, icon)
            root._icon_ref = icon  # prevent garbage collection
        except Exception:
            pass


def main() -> None:
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.0)
    except Exception:
        pass
    _set_icon(root)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
