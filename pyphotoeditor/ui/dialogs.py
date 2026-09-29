"""Validated, modal document-size dialogs."""
import tkinter as tk
from tkinter import messagebox
from . import theme as T
from .widgets import RoundedButton
from ..core.image_ops import validate_dimensions


def _size_dialog(parent,title,width,height,on_submit,allow_lock=False):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.grab_set()
    width_var = tk.StringVar(value=str(width))
    height_var = tk.StringVar(value=str(height))
    lock = tk.BooleanVar(value=allow_lock)
    for label,var in [('Width',width_var),('Height',height_var)]:
        tk.Label(dialog,text=label).pack(anchor='w',padx=T.PAD,pady=(T.PAD,T.SMALL))
        tk.Entry(dialog,textvariable=var).pack(padx=T.PAD)
    if allow_lock:
        tk.Checkbutton(dialog,text='Maintain aspect ratio',variable=lock).pack(pady=T.GAP)
    def submit(event=None):
        try:
            raw_w,raw_h = width_var.get(),height_var.get()
            if lock.get():
                new_w,_ = validate_dimensions(raw_w,1)
                raw_h = str(max(1,round(new_w*height/width)))
            new_w,new_h = validate_dimensions(raw_w,raw_h)
            on_submit(new_w,new_h)
        except (ValueError,MemoryError) as exc:
            messagebox.showerror('Invalid dimensions',str(exc),parent=dialog)
            return
        dialog.destroy()
    RoundedButton(dialog,text=title,command=submit).pack(padx=T.PAD,pady=T.PAD)
    dialog.bind('<Return>',submit)
    dialog.bind('<Escape>',lambda e:dialog.destroy())
    return dialog


def ask_new_image_size(parent,on_create):
    return _size_dialog(parent,'New image',*T.DEFAULT_IMAGE,on_create)


def ask_resize(parent,current_width,current_height,on_resize):
    return _size_dialog(parent,'Resize',current_width,current_height,on_resize,allow_lock=True)
