"""Small themed Canvas widgets, shared by the toolbar and tool options."""
import tkinter as tk
from tkinter import ttk
from functools import lru_cache
from PIL import Image, ImageDraw, ImageTk
from . import theme as T


@lru_cache(maxsize=128)
def icon_image(name, tint=T.TEXT):
    s = T.ICON_SIZE * 2
    im = Image.new('RGBA', (s, s))
    d = ImageDraw.Draw(im)
    # Deterministic, supersampled geometric glyphs; no external assets.
    kind = sum(map(ord, name)) % 4
    inset = T.SMALL
    box = (inset, inset, s-inset, s-inset)
    if kind == 0:
        d.ellipse(box, outline=tint, width=2)
        d.line((inset, s-inset, s-inset, inset), fill=tint, width=2)
    elif kind == 1:
        d.rectangle(box, outline=tint, width=2)
        d.line((inset, s//2, s-inset, s//2), fill=tint, width=2)
    elif kind == 2:
        d.polygon((s//2, inset, s-inset, s//2, s//2, s-inset, inset, s//2), outline=tint, width=2)
    else:
        d.line((inset, s-inset, s//2, inset, s-inset, s-inset), fill=tint, width=3)
    return im.resize((T.ICON_SIZE, T.ICON_SIZE), Image.Resampling.LANCZOS)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text='', command=None, icon=None, width=T.BUTTON_WIDTH, **kwargs):
        super().__init__(parent, width=width, height=T.BUTTON_HEIGHT, bg=T.BG_APP, highlightthickness=0, takefocus=True, **kwargs)
        self.text, self.command = text, command
        self.disabled = self.hover = self.pressed = self.selected = False
        self.icon = ImageTk.PhotoImage(icon_image(icon), master=self) if icon else None
        self.bind('<Configure>', lambda e: self.draw())
        self.bind('<Enter>', lambda e: self._state('hover', True))
        self.bind('<Leave>', lambda e: self._state('hover', False))
        self.bind('<ButtonPress-1>', lambda e: self._state('pressed', True))
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<space>', lambda e: self.invoke())
        self.bind('<Return>', lambda e: self.invoke())
        self.draw()

    def _state(self, key, value):
        setattr(self, key, value)
        self.draw()

    def set_disabled(self, value):
        self.disabled = value
        self.draw()

    def invoke(self):
        if not self.disabled and self.command:
            self.command()

    def _release(self, event):
        pressed = self.pressed
        self.pressed = False
        self.draw()
        if pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.invoke()

    def draw(self):
        self.delete('all')
        w = max(self.winfo_width(), int(self.cget('width')))
        h, r = T.BUTTON_HEIGHT, T.RADIUS
        bg = T.ACCENT if self.selected or self.pressed else T.BG_HOVER if self.hover else T.BG_SURFACE
        fg = T.TEXT_FAINT if self.disabled else T.TEXT
        self.create_polygon(r, 1, w-r, 1, w-1, 1, w-1, r, w-1, h-r, w-1, h-1, w-r, h-1, r, h-1, 1, h-1, 1, h-r, 1, r, 1, 1, smooth=True, fill=bg, outline=T.BORDER, width=T.BORDER_WIDTH)
        x = T.PAD
        if self.icon:
            self.create_image(x, h/2, image=self.icon, anchor='w')
            x += T.ICON_SIZE + T.GAP
        self.create_text(x, h/2, text=self.text, anchor='w', fill=fg, font=T.FONT)


class IconToggleButton(RoundedButton):
    def set_selected(self, selected):
        self.selected = selected
        self.draw()


class SegmentedControl(tk.Frame):
    def __init__(self, parent, values, variable, command=None):
        super().__init__(parent, bg=T.BG_APP)
        self.buttons = []
        for value in values:
            def choose(v=value):
                variable.set(v)
                if command:
                    command(v)
            button = IconToggleButton(self, text=value.title(), command=choose, width=T.SLIDER_WIDTH)
            button.pack(side='left', padx=T.BORDER_WIDTH)
            self.buttons.append((value, button))
        def update(*_):
            for value, button in self.buttons:
                button.set_selected(variable.get() == value)
        variable.trace_add('write', update)
        update()


class Slider(tk.Frame):
    def __init__(self, parent, label, variable, low, high, command=None):
        super().__init__(parent, bg=T.BG_APP)
        self.var, self.low, self.high, self.command = variable, low, high, command
        tk.Label(self, text=label, fg=T.TEXT_MUTED).pack(side='left', padx=T.SMALL)
        self.track = tk.Canvas(self, width=T.SLIDER_WIDTH, height=T.BUTTON_HEIGHT, highlightthickness=0, bg=T.BG_APP)
        self.track.pack(side='left')
        self.track.bind('<Button-1>', self.move)
        self.track.bind('<B1-Motion>', self.move)
        entry = ttk.Entry(self, textvariable=variable, width=T.ENTRY_WIDTH)
        entry.pack(side='left', padx=T.SMALL)
        entry.bind('<Return>', self.validate)
        entry.bind('<FocusOut>', self.validate)
        variable.trace_add('write', lambda *_: self.draw())
        self.draw()

    def validate(self, event=None):
        try:
            value = max(self.low, min(self.high, float(self.var.get())))
        except (ValueError, tk.TclError):
            value = self.low
        self.var.set(round(value, 2))
        if self.command:
            self.command(value)

    def move(self, event):
        value = self.low + (self.high-self.low)*max(0, min(1, event.x/T.SLIDER_WIDTH))
        self.var.set(round(value, 2))
        if self.command:
            self.command(value)

    def draw(self):
        try:
            fraction = (float(self.var.get())-self.low)/(self.high-self.low)
        except (ValueError, tk.TclError):
            return
        self.track.delete('all')
        y = T.BUTTON_HEIGHT/2
        x = max(0, min(1, fraction))*T.SLIDER_WIDTH
        self.track.create_line(0,y,T.SLIDER_WIDTH,y,fill=T.BORDER,width=T.SMALL)
        self.track.create_line(0,y,x,y,fill=T.ACCENT,width=T.SMALL)
        self.track.create_oval(x-T.SMALL,y-T.SMALL,x+T.SMALL,y+T.SMALL,fill=T.TEXT,outline=T.TEXT)


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.popup = widget, text, None
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<Leave>', self.hide, add='+')
        widget.bind('<Destroy>', self.hide, add='+')

    def show(self, event=None):
        self.hide()
        self.popup = tk.Toplevel(self.widget)
        self.popup.overrideredirect(True)
        self.popup.geometry(f'+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty()+T.BUTTON_HEIGHT}')
        tk.Label(self.popup,text=self.text,bg=T.BG_SURFACE,fg=T.TEXT,padx=T.PAD,pady=T.GAP).pack()

    def hide(self, event=None):
        if self.popup:
            self.popup.destroy()
            self.popup = None


class Panel(tk.Frame):
    def __init__(self, parent, title='', **kwargs):
        super().__init__(parent,bg=T.BG_SIDEBAR,highlightbackground=T.BORDER,highlightthickness=T.BORDER_WIDTH,**kwargs)
        if title:
            tk.Label(self,text=title,bg=T.BG_SIDEBAR,fg=T.TEXT_MUTED,font=T.FONT_HEADING).pack(anchor='w',padx=T.PAD,pady=T.GAP)


Card = Panel
