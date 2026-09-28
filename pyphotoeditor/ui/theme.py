"""All presentation tokens and platform styling live here."""
import tkinter as tk
from tkinter import ttk, font
BG_APP = '#212121'
BG_SIDEBAR = '#171717'
BG_SURFACE = '#2f2f2f'
BG_HOVER = '#3a3a3a'
BORDER = '#3a3a3a'
TEXT = '#ececec'
TEXT_MUTED = '#b4b4b4'
TEXT_FAINT = '#8e8e8e'
ACCENT = '#10a37f'
ACCENT_HOVER = '#0e8c6c'
DANGER = '#ef4444'
WORKSPACE = '#181818'
CHECKER = ('#3c3c3c', '#2c2c2c')
FONT = ('Segoe UI', 10)
FONT_HEADING = ('Segoe UI', 11, 'bold')
FONT_TITLE = ('Segoe UI', 16)
WINDOW_SIZE = '1400x900'
MIN_WINDOW = (1000, 700)
GAP = 8
PAD = 12
SMALL = 4
BORDER_WIDTH = 1
RADIUS = 10
BUTTON_HEIGHT = 32
BUTTON_WIDTH = 152
SIDEBAR_WIDTH = 184
PANEL_WIDTH = 236
SLIDER_WIDTH = 140
ENTRY_WIDTH = 5
ICON_SIZE = 18
CHECKER_SIZE = 12
MARQUEE_DASH = (5, 3)
DEFAULT_IMAGE = (1000, 700)
DEFAULT_BRUSH = 20
DEFAULT_COLOR = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


def install(root):
    global FONT, FONT_HEADING, FONT_TITLE
    families = set(font.families(root))
    face = next((f for f in ('Inter', 'Segoe UI', 'SF Pro Text', 'Helvetica') if f in families), 'TkDefaultFont')
    FONT, FONT_HEADING, FONT_TITLE = (face, 10), (face, 11, 'bold'), (face, 16)
    root.option_add('*Font', FONT)
    root.option_add('*Background', BG_APP)
    root.option_add('*Foreground', TEXT)
    root.option_add('*Entry.insertBackground', TEXT)
    root.option_add('*Menu.background', BG_SURFACE)
    root.option_add('*Menu.foreground', TEXT)
    root.option_add('*Menu.activeBackground', ACCENT)
    root.option_add('*Menu.activeForeground', TEXT)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=BG_APP, foreground=TEXT, fieldbackground=BG_SURFACE, bordercolor=BORDER, font=FONT)
    for name in ('TScrollbar', 'TCombobox', 'TEntry', 'TCheckbutton', 'TSeparator'):
        style.configure(name, background=BG_SURFACE, foreground=TEXT, fieldbackground=BG_SURFACE, arrowcolor=TEXT, bordercolor=BORDER)
        style.map(name, background=[('active', BG_HOVER)], foreground=[('disabled', TEXT_FAINT)])
    root.configure(bg=BG_APP)
    root.after_idle(lambda: dark_titlebar(root))


def dark_titlebar(root):
    try:
        import ctypes
        handle = ctypes.windll.user32.GetParent(root.winfo_id())
        enabled = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
    except (AttributeError, OSError, tk.TclError):
        pass
