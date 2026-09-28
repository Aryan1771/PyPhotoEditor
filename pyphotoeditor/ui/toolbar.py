import tkinter as tk
from . import theme as T
from .widgets import RoundedButton


def build_toolbar(parent,app):
    top = tk.Frame(parent,bg=T.BG_APP)
    top.pack(fill='x')
    for text,cmd in [('Open',app.open_image),('Save',app.save_image),('Undo',app.undo),('Redo',app.redo),('Fit',app.fit_to_window),('Properties',app.toggle_panel)]:
        RoundedButton(top,text=text,command=cmd,width=T.SLIDER_WIDTH).pack(side='left',padx=T.SMALL,pady=T.SMALL)
    label = tk.Label(top,text='100%',fg=T.TEXT_MUTED)
    label.pack(side='right',padx=T.PAD)
    return label
