import tkinter as tk
from tkinter import ttk
from . import theme as T
from .widgets import RoundedButton


def build_toolbar(parent,app):
    shell = tk.Frame(parent,bg=T.BG_SIDEBAR,highlightbackground=T.BORDER,highlightthickness=1)
    shell.pack(fill='x')
    top=tk.Frame(shell,bg=T.BG_SIDEBAR)
    top.pack(fill='x',padx=T.GAP,pady=T.SMALL)
    brand=tk.Label(top,text='PyPhotoEditor',bg=T.BG_SIDEBAR,fg=T.TEXT,font=T.FONT_HEADING)
    brand.pack(side='left',padx=(T.GAP,T.PAD))
    ttk.Separator(top,orient='vertical').pack(side='left',fill='y',padx=T.GAP)
    for text,cmd in [('Open',app.open_image),('Save',app.save_image),('Undo',app.undo),('Redo',app.redo),('Fit',app.fit_to_window)]:
        RoundedButton(top,text=text,command=cmd,width=94).pack(side='left',padx=T.BORDER_WIDTH,pady=T.BORDER_WIDTH)
    app.tool_options_toggle=RoundedButton(top,text='Tool settings  ▴',command=app.toggle_tool_options,width=140)
    app.tool_options_toggle.pack(side='left',padx=T.GAP)
    app.panel_toggle=RoundedButton(top,text='History panel',command=app.toggle_panel,width=124)
    app.panel_toggle.pack(side='left',padx=T.BORDER_WIDTH)
    label = tk.Label(top,text='100%',bg=T.BG_SIDEBAR,fg=T.TEXT_MUTED,padx=T.PAD)
    label.pack(side='right',padx=T.PAD)
    return label
