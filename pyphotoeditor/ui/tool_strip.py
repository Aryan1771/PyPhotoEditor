"""Grouped, scrollable tool sidebar."""
import tkinter as tk
from tkinter import ttk
from . import theme as T
from .widgets import IconToggleButton, Tooltip


def build_tool_strip(parent, app):
    strip = tk.Frame(parent,bg=T.BG_SIDEBAR,width=T.SIDEBAR_WIDTH)
    strip.pack(side='left',fill='y')
    strip.pack_propagate(False)
    canvas = tk.Canvas(strip,highlightthickness=0,bg=T.BG_SIDEBAR,width=T.SIDEBAR_WIDTH)
    scroll = ttk.Scrollbar(strip,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y')
    canvas.pack(side='left',fill='both',expand=True)
    content = tk.Frame(canvas,bg=T.BG_SIDEBAR)
    canvas.create_window(0,0,window=content,anchor='nw')
    content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
    def scroll_tools(event):
        canvas.yview_scroll(-1 if event.delta > 0 else 1,'units')
        return 'break'
    canvas.bind('<MouseWheel>',scroll_tools)
    content.bind('<MouseWheel>',scroll_tools)
    app.tool_buttons = {}
    previous = None
    for name, tool in app.tools.items():
        group = 'Magic effects' if hasattr(tool,'effect_key') else 'Drawing & selection'
        if group != previous:
            tk.Label(content,text=group,bg=T.BG_SIDEBAR,fg=T.TEXT_MUTED,font=T.FONT_HEADING).pack(anchor='w',padx=T.GAP,pady=T.GAP)
            previous = group
        label = getattr(tool,'label',name.title())
        button = IconToggleButton(content,text=label,icon=name,command=lambda n=name:app.select_tool(n))
        button.pack(fill='x',padx=T.SMALL,pady=T.BORDER_WIDTH)
        button.set_selected(name == 'brush')
        button.bind('<MouseWheel>',scroll_tools)
        Tooltip(button,label)
        app.tool_buttons[name] = button
    return strip
