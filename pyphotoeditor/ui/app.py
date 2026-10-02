"""
app
===
`App` is the composition root: it creates the Document, builds every UI
region by calling the other `ui` modules, and exposes the small set of
methods (open_image, grayscale, undo, ...) that those modules bind their
buttons/menu items to. `App` never contains a filter's *algorithm* --
those all live in `core` -- it only forwards to `core` and re-renders.
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

from ..core import Document, image_ops, filters, dithering, segmentation
from ..core.export import save_image as export_image
from ..core.image_io import load_image, SUPPORTED_EXTENSIONS
from . import menu_bar, toolbar, tool_strip, tool_panel, dialogs
from . import theme as T
from .canvas_view import CanvasView
from .tools import TOOL_CLASSES
from .tool_options import build_options
from .worker import OperationRunner


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        T.install(root)
        self.root.title("PyPhotoEditor — Python Image Editor")
        self.root.geometry(T.WINDOW_SIZE)
        self.root.minsize(*T.MIN_WINDOW)
        self.root.configure(bg=T.BG_APP)

        self.document = Document()
        self.source_path = None
        self.busy = False
        self.drawing = False
        self.runner = OperationRunner(self)
        self.brush_shape = "circle"
        self.brush_strength = 100
        self.brush_hardness = 100
        self.stroke_mode = "Once per stroke"
        self.effect_params = {}
        self.brush_size = T.DEFAULT_BRUSH
        self.brush_color = T.DEFAULT_COLOR
        self.gradient_start = (0, 0, 0, 255)
        self.gradient_end = (16, 163, 127, 255)
        self.gradient_options = {'type':'linear','direction':'horizontal'}
        self.wand_tolerance = 24
        self.active_symbol = None
        self.document.selection = None
        self.tools = {name: cls() for name, cls in TOOL_CLASSES.items()}
        self.active_tool = self.tools["brush"]

        self._build_layout()
        build_options(self)
        self._bind_shortcuts()
        self.history_list.bind("<<ListboxSelect>>", self._history_jump)
        self.refresh_history()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ---- layout construction -----------------------------------------
    def _build_layout(self):
        menu_bar.build_menu_bar(self.root, self)
        self.zoom_label = toolbar.build_toolbar(self.root, self)
        self.bottom_options=tk.Frame(self.root,bg=T.BG_SIDEBAR,highlightbackground=T.BORDER,highlightthickness=1)
        self.options = tk.Frame(self.bottom_options, bg=T.BG_APP)
        self.options.pack(fill='x',padx=T.GAP,pady=T.SMALL)
        self.options_open=True

        main = tk.Frame(self.root, bg=T.BG_APP)
        main.pack(fill="both", expand=True)

        tool_strip.build_tool_strip(main, self)

        center = tk.Frame(main, bg=T.WORKSPACE)
        center.pack(side="left", fill="both", expand=True)
        self.canvas_view = CanvasView(center, self)

        self.tool_var = tool_panel.build_tool_panel(main, self)

        self.status_var = tk.StringVar(value="Open an image to begin.")
        self.status_var_widget=tk.Label(self.root, textvariable=self.status_var, bg=T.BG_SURFACE, fg=T.TEXT_MUTED,
                 anchor="w", padx=T.PAD)
        self.status_var_widget.pack(side="bottom", fill="x")
        self.bottom_options.pack(side='bottom',fill='x',before=self.status_var_widget)

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_image())
        self.root.bind("<Control-s>", lambda e: self.save_image())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind("<Control-n>", lambda e: self.new_image())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<bracketleft>", lambda e: self.adjust_size(-5))
        self.root.bind("<bracketright>", lambda e: self.adjust_size(5))

    # ---- small shared UI callbacks -----------------------------------
    def status(self, text: str):
        self.status_var.set(text)

    def on_zoom_changed(self, scale_fraction: float):
        self.zoom_label.config(text=f"{int(scale_fraction * 100)}%")

    def select_tool(self, name: str):
        self.active_tool.on_up(self, None)
        self.active_tool = self.tools[name]
        build_options(self)
        self.tool_var.set(getattr(self.active_tool,"label",name.title()))
        self.status(f"Tool: {self.tool_var.get()}")
        for key, button in self.tool_buttons.items():
            button.set_selected(key == name)

    def refresh_history(self):
        self.document.finish_pending()
        self.update_title()
        self.history_list.delete(0, "end")
        self.history_list.insert("end", "Initial / retained state")
        for command in self.document.history:
            self.history_list.insert("end", command.name)
        self.history_list.selection_set(self.document.history_index)
        if "restore" in self.tool_buttons:
            self.tool_buttons["restore"].set_disabled(not self.document.can_restore)

    def update_title(self):
        path = self.document.filepath or self.source_path
        name = os.path.basename(path) if path else "Untitled"
        marker = "* " if self.document.dirty else ""
        self.root.title(f"{marker}{name} — PyPhotoEditor")

    def confirm_replace(self):
        if not self.document.dirty:
            return True
        answer = messagebox.askyesnocancel("Unsaved changes", "Save your changes before continuing?", parent=self.root)
        if answer is None:
            return False
        return bool(self.save_image()) if answer else True

    def close(self):
        if not self.confirm_replace():
            return
        self.runner.shutdown()
        self.root.destroy()

    def _history_jump(self, event):
        selected = self.history_list.curselection()
        if selected:
            self.document.jump_to(selected[0])
            self.update_title()
            self.canvas_view.render()
            self.tool_buttons["restore"].set_disabled(not self.document.can_restore)

    def toggle_panel(self):
        if self.right_panel.winfo_manager():
            self.right_panel.pack_forget()
        else:
            self.right_panel.pack(side="right", fill="y")

    def toggle_tool_options(self):
        if self.options_open:
            self.options.pack_forget()
            self.options_open=False
            self.tool_options_toggle.text='Tool settings  ▾'; self.tool_options_toggle.draw()
        else:
            self.options.pack(fill='x',padx=T.GAP,pady=T.SMALL)
            self.options_open=True
            self.tool_options_toggle.text='Tool settings  ▴'; self.tool_options_toggle.draw()

    def adjust_size(self, delta):
        if self.root.focus_get() and self.root.focus_get().winfo_class() in ("Entry", "TEntry"):
            return
        self.set_brush_size(self.brush_size + delta)
        if hasattr(self, "size_var"):
            self.size_var.set(self.brush_size)

    def set_brush_size(self, value):
        self.brush_size = max(1, min(500, int(float(value))))

    def set_brush_color(self, rgba):
        self.brush_color = rgba

    def clear_selection(self):
        self.document.selection=None
        self.canvas_view.render()
        self.status('Selection cleared.')

    def symbol_studio(self):
        """Open an offline pixel/brush/local-symbol creation workspace."""
        from tkinter import colorchooser
        from tkinter import filedialog, ttk
        from PIL import Image,ImageDraw,ImageTk
        win=tk.Toplevel(self.root); win.title('Symbol Studio'); win.transient(self.root); win.geometry('720x570')
        tabs=ttk.Notebook(win); tabs.pack(fill='both',expand=True,padx=T.PAD,pady=T.PAD)
        pixel_tab=tk.Frame(tabs); brush_tab=tk.Frame(tabs); local_tab=tk.Frame(tabs)
        tabs.add(pixel_tab,text='Pixel art'); tabs.add(brush_tab,text='Paint'); tabs.add(local_tab,text='PC images')
        color=tk.StringVar(value='#10a37f'); grid=tk.IntVar(value=24); pixel_size=10
        preview=tk.Canvas(pixel_tab,width=240,height=240,bg='#eeeeee',highlightthickness=0); preview.pack(padx=T.PAD,pady=T.PAD)
        tk.Label(pixel_tab,text='Paint individual cells, then use the result as a stamp.',fg=T.TEXT_MUTED).pack()
        control=tk.Frame(pixel_tab); control.pack(pady=T.GAP)
        ttk.Spinbox(control,from_=8,to=48,textvariable=grid,width=5).pack(side='left',padx=T.GAP)
        tk.Entry(control,textvariable=color,width=10).pack(side='left')
        tk.Button(control,text='Color…',command=lambda:color.set(colorchooser.askcolor(parent=win)[1] or color.get())).pack(side='left',padx=T.GAP)
        symbols=[None]
        def new_grid():
            size=int(grid.get()); symbols[0]=Image.new('RGBA',(size,size),(0,0,0,0)); preview.delete('all')
            preview.create_rectangle(0,0,240,240,fill='white',outline='')
            for i in range(size+1):
                p=i*240/size; preview.create_line(p,0,p,240,fill='#cccccc'); preview.create_line(0,p,240,p,fill='#cccccc')
            preview.bind('<Button-1>',paint_cell); preview.bind('<B1-Motion>',paint_cell)
        def paint_cell(event):
            size=symbols[0].width; x=min(size-1,max(0,int(event.x/240*size))); y=min(size-1,max(0,int(event.y/240*size)))
            try: fill=color.get()
            except Exception: return
            ImageDraw.Draw(symbols[0]).rectangle((x,y,x,y),fill=fill)
            step=240/size; preview.create_rectangle(x*step,y*step,(x+1)*step,(y+1)*step,fill=fill,outline='#cccccc')
        def use_symbol(image): self.active_symbol=image.convert('RGBA'); self.brush_size=max(1,min(500,max(image.size))); self.select_tool('symbol'); win.destroy()
        ttk.Button(control,text='New grid',command=new_grid).pack(side='left',padx=T.GAP)
        ttk.Button(control,text='Use as stamp',command=lambda:use_symbol(symbols[0]) if symbols[0] else None).pack(side='left')
        new_grid()
        brush_canvas=tk.Canvas(brush_tab,width=480,height=300,bg='white'); brush_canvas.pack(padx=T.PAD,pady=T.PAD)
        tk.Label(brush_tab,text='Draw freely, choose a brush color and size, then use your drawing as a stamp.',fg=T.TEXT_MUTED).pack()
        brush_image=Image.new('RGBA',(480,300),(0,0,0,0)); draw_state=[None]; art_color=[self.brush_color]
        brush_controls=tk.Frame(brush_tab); brush_controls.pack(pady=T.GAP)
        ttk.Button(brush_controls,text='Brush color…',command=lambda:self._choose_symbol_brush_color(colorchooser,art_color)).pack(side='left',padx=T.GAP)
        brush_width=tk.IntVar(value=max(2,self.brush_size//3))
        ttk.Label(brush_controls,text='Brush size').pack(side='left')
        ttk.Scale(brush_controls,from_=2,to=60,variable=brush_width,orient='horizontal').pack(side='left',padx=T.GAP)
        def start(event): draw_state[0]=(event.x,event.y); brush_canvas.bind('<B1-Motion>',paint_brush)
        def paint_brush(event):
            x,y=draw_state[0]; fill=tuple(art_color[0]); width=max(2,int(brush_width.get())); ImageDraw.Draw(brush_image).line((x,y,event.x,event.y),fill=fill,width=width); brush_canvas.create_line(x,y,event.x,event.y,fill='#'+''.join(f'{v:02x}' for v in fill[:3]),width=width,capstyle='round'); draw_state[0]=(event.x,event.y)
        brush_canvas.bind('<Button-1>',start)
        ttk.Button(brush_tab,text='Use as stamp',command=lambda:use_symbol(brush_image)).pack(pady=T.GAP)
        tk.Label(local_tab,text='Load a transparent or ordinary image from this PC; it stays on your computer.',fg=T.TEXT_MUTED).pack(pady=T.PAD)
        local_preview=tk.Label(local_tab); local_preview.pack(expand=True)
        chosen=[None]
        def load_symbol():
            path=filedialog.askopenfilename(parent=win,filetypes=[('Images','*.png *.webp *.bmp *.gif *.tif *.tiff *.jpg *.jpeg'),('All files','*.*')])
            if not path:return
            try:
                image=Image.open(path).convert('RGBA'); image.thumbnail((360,300)); chosen[0]=image
                thumb=image.copy(); thumb.thumbnail((240,200)); self._symbol_preview=ImageTk.PhotoImage(thumb,master=win); local_preview.configure(image=self._symbol_preview)
            except Exception as exc: messagebox.showerror('Symbol error',str(exc),parent=win)
        ttk.Button(local_tab,text='Choose image…',command=load_symbol).pack(pady=T.GAP)
        ttk.Button(local_tab,text='Use as stamp',command=lambda:use_symbol(chosen[0]) if chosen[0] else None).pack()

    def _choose_symbol_brush_color(self,colorchooser,target):
        result=colorchooser.askcolor(parent=self.root,color='#'+''.join(f'{v:02x}' for v in self.brush_color[:3]))
        if result[0]: target[0]=(*map(int,result[0]),255)

    def choose_gradient_color(self,which):
        from tkinter import colorchooser
        result=colorchooser.askcolor(parent=self.root)
        if result[0]: setattr(self,'gradient_'+which,(*map(int,result[0]),255))

    # ---- document lifecycle -------------------------------------------
    def new_image(self):
        if not self.confirm_replace():
            return
        dialogs.ask_new_image_size(self.root, self._create_new_document)

    def _create_new_document(self, width, height):
        self.document.new(width, height)
        self.source_path = None
        self.update_title()
        self.refresh_history()
        self.canvas_view.render()
        self.status("New document created.")

    def open_image(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                parent=self.root,
                title="Open image in PyPhotoEditor",
                filetypes=[("Images", " ".join("*"+ext for ext in SUPPORTED_EXTENSIONS)), ("All files", "*.*")],
            )
        if not path:
            return False
        try:
            loaded = load_image(path)
            if not self.confirm_replace():
                return False
            self.document.load(loaded.image, filepath=loaded.save_path)
            self.source_path = loaded.source
            self.refresh_history()
            self.canvas_view.fit_to_window()
            self.root.title(f"{os.path.basename(path)} — PyPhotoEditor")
            detail = f"; editing first of {loaded.frames} frames/pages" if loaded.frames > 1 else ""
            self.status(f"Opened {os.path.basename(path)} ({loaded.format}){detail}")
            return True
        except Exception as exc:
            messagebox.showerror("Open error", f"Could not open this image.\n\n{exc}", parent=self.root)
            return False

    def save_image(self):
        if self.document.image is None:
            return False
        if not self.document.filepath:
            return self.save_as()
        return self._save_to(self.document.filepath)

    def _save_to(self, path):
        if self.document.image is None:
            return False
        try:
            if str(path).lower().endswith((".jpg", ".jpeg")):
                if not messagebox.askokcancel("JPEG transparency", "JPEG cannot preserve transparency. Save flattened onto white?", parent=self.root):
                    return False
            export_image(self.document.image, path)
            self.document.filepath = os.path.abspath(path)
            self.source_path = self.document.filepath
            self.document.mark_saved()
            self.update_title()
            self.status("Saved.")
            return True
        except Exception as exc:
            messagebox.showerror("Save error", str(exc), parent=self.root)
            return False

    def save_as(self):
        if self.document.image is None:
            return False
        path = filedialog.asksaveasfilename(
            parent=self.root,
            initialfile=os.path.splitext(os.path.basename(self.source_path))[0]+".png" if self.source_path else "Untitled.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp"), ("TIFF", "*.tiff")],
        )
        return self._save_to(path) if path else False

    def undo(self):
        self.active_tool.on_up(self, None)
        if self.document.undo():
            self.refresh_history()
            self.canvas_view.render()

    def redo(self):
        self.active_tool.on_up(self, None)
        if self.document.redo():
            self.refresh_history()
            self.canvas_view.render()

    def reset(self):
        self.active_tool.on_up(self, None)
        self.document.reset_to_original()
        self.refresh_history()
        self.canvas_view.render()

    def fit_to_window(self):
        self.canvas_view.fit_to_window()

    # ---- image ops / filters (all just: apply + re-render) -----------
    def grayscale(self):
        self._apply(image_ops.grayscale)

    def invert(self):
        self._apply(image_ops.invert)

    def auto_contrast(self):
        self._apply(image_ops.auto_contrast)

    def flip_horizontal(self):
        self._apply(image_ops.flip_horizontal)

    def flip_vertical(self):
        self._apply(image_ops.flip_vertical)

    def rotate(self, degrees):
        self._apply(lambda img: image_ops.rotate(img, degrees), f"Rotate {degrees}°")

    def resize_dialog(self):
        if self.document.image is None:
            return
        w, h = self.document.size
        dialogs.ask_resize(self.root, w, h, lambda nw, nh: self._apply(lambda img: image_ops.resize(img, nw, nh), "Resize"))

    def gaussian_blur(self):
        self._apply(filters.gaussian_blur)

    def median_filter(self):
        self._apply(filters.median_filter)

    def unsharp_mask(self):
        self._apply(filters.unsharp_mask)

    def sobel_edges(self):
        self._apply(filters.sobel_edges)

    def canny_edges(self):
        self._apply(filters.canny_edges)

    def clahe(self):
        self._apply(filters.clahe)

    def denoise_tv(self):
        self._apply(filters.denoise_tv)

    def dither(self):
        self._apply(dithering.floyd_steinberg)

    def posterize(self):
        self._apply(segmentation.kmeans_posterize)

    def rotoscope(self):
        self._apply(segmentation.rotoscope)

    def _apply(self, transform, name=None):
        if self.document.image is None:
            return
        name = name or getattr(transform, "__name__", "Image operation").replace("_", " ").title()
        self.runner.start(transform, name)


def _after_stroke(method):
    """Serialize document commands behind any queued pointer samples."""
    from functools import wraps
    @wraps(method)
    def call(self,*args,**kwargs):
        if self.drawing:
            self.active_tool.on_up(self,None)
            self.root.after(T.POLL_MS,lambda:call(self,*args,**kwargs))
            return
        return method(self,*args,**kwargs)
    return call


for _method in ('close','select_tool','new_image','_create_new_document','open_image','save_image','save_as','undo','redo','reset','_apply','_history_jump','clear_selection'):
    setattr(App,_method,_after_stroke(getattr(App,_method)))
