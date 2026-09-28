"""Pointer tools delegate all pixel operations to the headless core."""
from ..core.brush import Brush
from ..core.stroke import StrokeSession, union
from ..core.bg_eraser import prepare
from collections import deque
import time
from tkinter import messagebox
from . import theme as T
from ..core.brush_effects import EFFECTS
from ..core import drawing, image_ops


class BaseTool:
    name = 'base'
    def on_down(self,app,point):
        return None
    def on_move(self,app,point):
        return None
    def on_up(self,app,point):
        return None


class BrushTool(BaseTool):
    name = 'brush'
    engine_key = 'paint'
    session = None

    def __init__(self):
        self.next_strokes = deque()
        self.queued_active = None

    def on_down(self,app,point):
        if app.document.image is None:
            return
        if app.drawing:
            self.queued_active = {'points':[point], 'released':False}
            self.next_strokes.append(self.queued_active)
            return
        if app.busy:
            return
        brush = Brush(app.brush_shape,app.brush_size,app.brush_hardness,app.brush_strength)
        key = getattr(self,'effect_key',self.engine_key)
        if key == 'restore' and not app.document.can_restore:
            app.status('Restore unavailable: canvas dimensions differ from the original.')
            return
        params = dict(app.effect_params.get(key,{}),color=app.brush_color)
        # Keep the immutable image reference until preparation ends. Document actions
        # are deferred by App while a stroke is being prepared or drained.
        source = app.document.image
        mode = app.stroke_mode
        self.pending = deque([point])
        self.iterator = None
        self.released = False
        self.session = None
        app.drawing = True
        def work():
            session = StrokeSession(app.document,EFFECTS[key],brush,mode,params,source_image=source)
            if key == 'background_eraser':
                session.state.update(prepare(session.base,session.params,point,brush))
            return session
        def ready(session):
            self.session = session
            self._drain(app)
        def cancel():
            self.pending.clear()
            self.next_strokes.clear()
            self.queued_active = None
            self.session = None
            app.drawing = False
        app.runner.submit(work,'Prepare '+EFFECTS[key].name,ready,cancel,show_progress=key == 'background_eraser')

    def on_move(self,app,point):
        if self.queued_active is not None:
            if point is not None:
                self.queued_active['points'].append(point)
            return
        if app.drawing and not self.released and point is not None:
            if not self.pending or self.pending[-1] != point:
                self.pending.append(point)

    def on_up(self,app,point):
        if self.queued_active is not None:
            self.on_move(app,point)
            self.queued_active['released'] = True
            self.queued_active = None
            return
        if app.drawing:
            self.on_move(app,point)
            self.released = True

    def _drain(self,app):
        if self.session is None:
            return
        started = time.perf_counter()
        dirty = None
        try:
            while time.perf_counter()-started < T.STROKE_BATCH_SECONDS:
                if self.iterator is None:
                    if not self.pending:
                        break
                    self.iterator = self.session.iter_move(self.pending.popleft())
                try:
                    dirty = union(dirty,next(self.iterator))
                except StopIteration:
                    self.iterator = None
            self.session.publish(dirty)
            app.canvas_view.render_dirty(dirty)
            if self.released and not self.pending and self.iterator is None:
                box = self.session.dirty
                self.session.finish()
                app.canvas_view.render_dirty(union(box,self.session.dirty))
                self.session = None
                app.drawing = False
                app.refresh_history()
                if self.next_strokes:
                    queued = self.next_strokes.popleft()
                    if self.queued_active is queued:
                        self.queued_active = None
                    self.on_down(app,queued['points'][0])
                    self.pending.extend(queued['points'][1:])
                    self.released = queued['released']
            else:
                app.root.after(1,lambda:self._drain(app))
        except Exception as exc:
            self.session.cancel()
            self.session = None
            app.drawing = False
            self.next_strokes.clear()
            self.queued_active = None
            app.canvas_view.render()
            messagebox.showerror('Brush failed',str(exc),parent=app.root)


class PencilTool(BrushTool):
    name = 'pencil'


class EraserTool(BrushTool):
    name = 'eraser'
    engine_key = 'erase'


class ShapeTool(BaseTool):
    box = None
    def on_down(self,app,point):
        self.box = [*point,*point]
    def on_move(self,app,point):
        if self.box:
            self.box[2:] = point
            app.canvas_view.draw_marquee(self.box)
    def on_up(self,app,point):
        if self.box is None:
            return
        if point:
            self.box[2:] = point
        x1,y1,x2,y2 = self.box
        box = (min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2))
        self.box = None
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        if self.name == 'crop':
            app.document.apply(lambda image:image_ops.crop(image,box),'Crop')
        else:
            app.document.apply(lambda image:drawing.shape(image,box,self.kind,app.brush_color,max(1,app.brush_size//4)),self.kind.title())


class RectangleTool(ShapeTool):
    name,kind = 'rect','rectangle'


class EllipseTool(ShapeTool):
    name,kind = 'ellipse','ellipse'


class CropTool(ShapeTool):
    name = 'crop'


class EyedropperTool(BaseTool):
    name = 'eyedropper'
    def on_down(self,app,point):
        if app.document.image is not None:
            app.set_brush_color(app.document.image.getpixel(point))


TOOL_CLASSES = {cls.name:cls for cls in (BrushTool,PencilTool,EraserTool,RectangleTool,EllipseTool,CropTool,EyedropperTool)}
for key,effect in EFFECTS.items():
    if key not in ('paint','erase'):
        TOOL_CLASSES[key] = type(key.title()+'Tool',(BrushTool,),{'name':key,'effect_key':key,'label':effect.name})
