import tkinter as tk
from tkinter import colorchooser
from . import theme as T
from .widgets import Panel, RoundedButton, Slider


def build_tool_panel(parent,app):
    panel = Panel(parent,'PROPERTIES / HISTORY',width=T.PANEL_WIDTH)
    panel.pack(side='right',fill='y')
    panel.pack_propagate(False)
    app.right_panel = panel
    tool_var = tk.StringVar(value='Brush')
    tk.Label(panel,textvariable=tool_var,bg=T.BG_SIDEBAR).pack(anchor='w',padx=T.PAD)
    def choose():
        result = colorchooser.askcolor(parent=app.root)
        if result[0]:
            app.set_brush_color((*map(int,result[0]),255))
    RoundedButton(panel,text='Choose color',command=choose).pack(padx=T.PAD,pady=T.GAP)
    tk.Label(panel,text='Quick filters',bg=T.BG_SIDEBAR,fg=T.TEXT_MUTED).pack(anchor='w',padx=T.PAD,pady=T.GAP)
    for text,cmd in [('Grayscale',app.grayscale),('Gaussian Blur',app.gaussian_blur),('Median',app.median_filter),('Sobel',app.sobel_edges),('Canny',app.canny_edges),('Dither',app.dither),('K-Means',app.posterize),('Rotoscope',app.rotoscope)]:
        RoundedButton(panel,text=text,command=cmd).pack(fill='x',padx=T.PAD,pady=T.BORDER_WIDTH)
    tk.Label(panel,text='History',bg=T.BG_SIDEBAR,fg=T.TEXT_MUTED).pack(anchor='w',padx=T.PAD,pady=T.GAP)
    app.history_list = tk.Listbox(panel,bg=T.BG_SURFACE,fg=T.TEXT,selectbackground=T.ACCENT,relief='flat',highlightthickness=0,exportselection=False)
    app.history_list.pack(fill='both',expand=True,padx=T.PAD,pady=T.GAP)
    return tool_var
