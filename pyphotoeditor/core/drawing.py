"""Pure drawing transforms used by the rectangle/ellipse drag-box tools."""
from PIL import ImageDraw


def shape(image,box,kind,color,width):
    out = image.copy()
    draw = ImageDraw.Draw(out)
    getattr(draw,kind)(box,outline=color,width=width)
    return out
