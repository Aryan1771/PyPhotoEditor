"""Pointer tools delegate all pixel operations to the headless core."""
from ..core.brush import Brush
from ..core.stroke import StrokeSession
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

    def on_down(self,app,point):
        if app.document.image is None:
            return
        if self.session:
            self.session.finish()
        brush = Brush(app.brush_shape,app.brush_size,app.brush_hardness,app.brush_strength)
        key = getattr(self,'effect_key',self.engine_key)
        if key == 'restore' and not app.document.can_restore:
            app.status('Restore unavailable: canvas dimensions differ from the original.')
            return
        params = dict(app.effect_params.get(key,{}),color=app.brush_color)
        self.session = StrokeSession(app.document,EFFECTS[key],brush,app.stroke_mode,params)
        app.canvas_view.render_dirty(self.session.move_to(point))

    def on_move(self,app,point):
        if self.session:
            app.canvas_view.render_dirty(self.session.move_to(point))

    def on_up(self,app,point):
        if self.session:
            if point is not None and point != self.session.last:
                self.session.move_to(point)
            self.session.finish()
            self.session = None


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
