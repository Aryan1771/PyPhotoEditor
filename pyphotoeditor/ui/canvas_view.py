"""Viewport rendering, dirty patch updates, zoom, pan and pointer routing."""
import math
import tkinter as tk
import numpy as np
from PIL import Image, ImageTk, ImageColor
from . import theme as T


class CanvasView:
    def __init__(self, parent, app):
        self.app = app
        self.zoom = 1.0
        self.display_size = (1, 1)
        self.image_origin = (0, 0)
        self.offset = [0, 0]
        self._tk_image = None
        self._space = False
        self._pan = None
        self.widget = tk.Canvas(parent, bg=T.WORKSPACE, highlightthickness=0, cursor='crosshair')
        self.widget.pack(fill='both', expand=True)
        for event, fn in {'<Configure>':lambda e:self.render(), '<ButtonPress-1>':self._on_down,
                          '<B1-Motion>':self._on_move, '<ButtonRelease-1>':self._on_up,
                          '<Motion>':self._cursor, '<Leave>':lambda e:self.widget.delete('cursor'),
                          '<MouseWheel>':self._on_wheel, '<Button-4>':lambda e:self.zoom_by(1.1,e),
                          '<Button-5>':lambda e:self.zoom_by(1/1.1,e),
                          '<ButtonPress-2>':self._pan_start, '<B2-Motion>':self._pan_move,
                          '<ButtonRelease-2>':self._pan_end}.items():
            self.widget.bind(event, fn)
        app.root.bind('<KeyPress-space>', lambda e:setattr(self,'_space',True))
        app.root.bind('<KeyRelease-space>', lambda e:setattr(self,'_space',False))
        app.root.bind('<FocusOut>', lambda e:setattr(self,'_space',False))

    def _canvas_size(self):
        return max(1,self.widget.winfo_width()), max(1,self.widget.winfo_height())

    def _composite(self, image, x, y):
        a = np.asarray(image.convert('RGBA'))
        yy,xx = np.ogrid[y:y+a.shape[0], x:x+a.shape[1]]
        grid = ((xx//T.CHECKER_SIZE + yy//T.CHECKER_SIZE) % 2)
        colors = np.array([ImageColor.getrgb(c) for c in T.CHECKER], dtype=np.float32)
        alpha = a[...,3:4].astype(np.float32)/255
        return Image.fromarray(np.rint(a[...,:3]*alpha + colors[grid]*(1-alpha)).astype(np.uint8))

    def _resize_region(self, image, size, box):
        l,t,r,b = box
        crop = (max(0,math.floor(l)-1),max(0,math.floor(t)-1),min(image.width,math.ceil(r)+1),min(image.height,math.ceil(b)+1))
        region = image.crop(crop)
        return region.resize(size,Image.Resampling.BILINEAR,box=(l-crop[0],t-crop[1],r-crop[0],b-crop[1]))

    def render(self):
        self.widget.delete('all')
        doc = self.app.document
        cw,ch = self._canvas_size()
        if doc.image is None:
            self.widget.create_text(cw/2,ch/2,text='Open an image or create a new document',fill=T.TEXT_FAINT,font=T.FONT_TITLE)
            return
        iw,ih = doc.size
        scale = max(0.01,min(16,min(max(1,cw-2*T.PAD)/iw,max(1,ch-2*T.PAD)/ih)*self.zoom))
        self.display_size = (max(1,round(iw*scale)),max(1,round(ih*scale)))
        dw,dh = self.display_size
        self.image_origin = ((cw-dw)//2+self.offset[0],(ch-dh)//2+self.offset[1])
        ox,oy = self.image_origin
        # Render only the visible viewport; zoomed 12 MP images never allocate giant previews.
        self.viewport = (max(0,-ox),max(0,-oy),min(dw,cw-ox),min(dh,ch-oy))
        l,t,r,b = self.viewport
        if r <= l or b <= t:
            self._tk_image = None
            return
        box = (l*iw/dw,t*ih/dh,r*iw/dw,b*ih/dh)
        preview = self._resize_region(doc.image,(r-l,b-t),box)
        self._tk_image = ImageTk.PhotoImage(self._composite(preview,l,t))
        self.widget.create_rectangle(ox-1,oy-1,ox+dw+1,oy+dh+1,outline=T.BORDER,width=T.BORDER_WIDTH)
        self.widget.create_image(ox+l,oy+t,anchor='nw',image=self._tk_image)
        self.app.on_zoom_changed(dw/iw)

    def render_dirty(self, bbox):
        if not bbox or self._tk_image is None:
            return
        doc = self.app.document
        dw,dh = self.display_size
        iw,ih = doc.size
        vl,vt,vr,vb = self.viewport
        l = max(vl,math.floor(bbox[0]*dw/iw)-1)
        t = max(vt,math.floor(bbox[1]*dh/ih)-1)
        r = min(vr,math.ceil(bbox[2]*dw/iw)+1)
        b = min(vb,math.ceil(bbox[3]*dh/ih)+1)
        if r <= l or b <= t:
            return
        preview = self._resize_region(doc.image,(r-l,b-t),(l*iw/dw,t*ih/dh,r*iw/dw,b*ih/dh))
        patch = ImageTk.PhotoImage(self._composite(preview,l,t))
        self.widget.tk.call(str(self._tk_image),'copy',str(patch),'-to',l-vl,t-vt)

    def draw_marquee(self, box):
        self.widget.delete('marquee')
        ox,oy = self.image_origin
        sx,sy = self.display_size[0]/self.app.document.size[0],self.display_size[1]/self.app.document.size[1]
        self.widget.create_rectangle(ox+box[0]*sx,oy+box[1]*sy,ox+box[2]*sx,oy+box[3]*sy,outline=T.TEXT,dash=T.MARQUEE_DASH,width=T.BORDER_WIDTH,tags='marquee')

    def fit_to_window(self):
        self.zoom = 1.0
        self.offset = [0,0]
        self.render()

    def zoom_by(self, factor, event=None):
        if self.app.document.image is None:
            return
        cw,ch = self._canvas_size()
        x,y = (event.x,event.y) if event else (cw/2,ch/2)
        old = self.display_size
        rel = ((x-self.image_origin[0])/old[0],(y-self.image_origin[1])/old[1])
        self.zoom = max(0.05,min(32,self.zoom*factor))
        self.render()
        dw,dh = self.display_size
        self.offset = [round(x-rel[0]*dw-(cw-dw)//2),round(y-rel[1]*dh-(ch-dh)//2)]
        self.render()

    def to_image_point(self,x,y):
        doc = self.app.document
        if doc.image is None:
            return None
        ox,oy = self.image_origin
        dw,dh = self.display_size
        if ox <= x < ox+dw and oy <= y < oy+dh:
            return int((x-ox)*doc.image.width/dw),int((y-oy)*doc.image.height/dh)

    def _cursor(self,event):
        self.widget.delete('cursor')
        p = self.to_image_point(event.x,event.y)
        tool = self.app.active_tool
        brush = tool.name in ('brush','pencil','eraser') or hasattr(tool,'effect_key')
        self.widget.configure(cursor='none' if p and brush else 'crosshair')
        if p:
            self.app.status(f'{self.display_size[0]/self.app.document.size[0]:.0%}  |  x {p[0]}, y {p[1]}  |  {self.app.document.size[0]} × {self.app.document.size[1]}  |  {tool.name.title()} — drag to apply; Space to pan')
            if brush:
                radius = self.app.brush_size*self.display_size[0]/self.app.document.size[0]/2
                shape = getattr(self.app,'brush_shape','circle')
                draw = self.widget.create_rectangle if shape == 'square' else self.widget.create_oval
                draw(event.x-radius,event.y-radius,event.x+radius,event.y+radius,outline=T.TEXT,width=T.BORDER_WIDTH,tags='cursor')

    def _on_down(self,event):
        if self._space:
            return self._pan_start(event)
        if getattr(self.app,'busy',False):
            return
        p = self.to_image_point(event.x,event.y)
        if p:
            self.app.active_tool.on_down(self.app,p)
            if not hasattr(self.app.active_tool,'session'):
                self.render()

    def _on_move(self,event):
        if self._pan:
            return self._pan_move(event)
        if getattr(self.app,'busy',False) and not getattr(self.app,'drawing',False):
            return
        p = self.to_image_point(event.x,event.y)
        if p:
            self.app.active_tool.on_move(self.app,p)
            if self.app.active_tool.name in ('brush','pencil','eraser') and not hasattr(self.app.active_tool,'session'):
                self.render()
        self._cursor(event)

    def _on_up(self,event):
        if self._pan:
            return self._pan_end(event)
        if getattr(self.app,'busy',False) and not getattr(self.app,'drawing',False):
            return
        p = self.to_image_point(event.x,event.y)
        self.app.active_tool.on_up(self.app,p)
        self.widget.delete('marquee')
        if hasattr(self.app.active_tool,'session'):
            return
        self.render()
        if hasattr(self.app,'refresh_history'):
            self.app.refresh_history()

    def _on_wheel(self,event):
        self.zoom_by(1.1 if event.delta > 0 else 1/1.1,event)

    def _pan_start(self,event):
        self._pan = (event.x,event.y,*self.offset)

    def _pan_move(self,event):
        if self._pan:
            x,y,ox,oy = self._pan
            self.offset = [ox+event.x-x,oy+event.y-y]
            self.render()

    def _pan_end(self,event):
        self._pan = None
