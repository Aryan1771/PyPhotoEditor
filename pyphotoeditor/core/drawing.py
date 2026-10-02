"""Pure drawing transforms and gradient fills used by the canvas tools."""
import numpy as np
from PIL import Image, ImageDraw


def shape(image,box,kind,color,width):
    out = image.copy()
    draw = ImageDraw.Draw(out)
    getattr(draw,kind)(box,outline=color,width=width)
    return out


def gradient(image, box, start, end, kind='linear', direction='horizontal'):
    """Create a clipped two-color linear/radial gradient in an image region."""
    x1,y1,x2,y2 = map(int,box)
    x1,x2 = sorted((max(0,x1),min(image.width,x2)))
    y1,y2 = sorted((max(0,y1),min(image.height,y2)))
    if x2 <= x1 or y2 <= y1:
        return image.copy()
    w,h = x2-x1,y2-y1
    xx,yy = np.meshgrid(np.linspace(0,1,w,dtype=np.float32),np.linspace(0,1,h,dtype=np.float32))
    if kind == 'radial':
        amount = np.clip(np.sqrt(((xx-.5)*2)**2+((yy-.5)*2)**2),0,1)
    elif direction == 'vertical':
        amount = yy
    elif direction == 'diagonal':
        amount = np.clip((xx+yy)*.5,0,1)
    else:
        amount = xx
    a=np.asarray(start.convert('RGBA') if isinstance(start,Image.Image) else start,dtype=np.float32)
    b=np.asarray(end.convert('RGBA') if isinstance(end,Image.Image) else end,dtype=np.float32)
    pixels=np.rint(a[None,None,:]+(b-a)[None,None,:]*amount[...,None]).clip(0,255).astype(np.uint8)
    layer=Image.fromarray(pixels)
    out=image.convert('RGBA').copy()
    out.alpha_composite(layer,(x1,y1))
    return out


def stamp(image, symbol, point, size, opacity=1.0):
    """Stamp a local RGBA symbol centered on image coordinates."""
    symbol=symbol.convert('RGBA')
    size=max(1,int(size))
    symbol.thumbnail((size,size),Image.Resampling.LANCZOS)
    if opacity < 1:
        alpha=symbol.getchannel('A').point(lambda a:int(a*max(0,min(1,opacity))))
        symbol.putalpha(alpha)
    x,y=map(int,point)
    out=image.convert('RGBA').copy()
    out.alpha_composite(symbol,(x-symbol.width//2,y-symbol.height//2))
    return out
