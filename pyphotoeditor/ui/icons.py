"""Programmatically generated, theme-tinted application icon."""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from . import theme as T


@lru_cache(maxsize=1)
def app_icon():
    size = T.LOGO_SIZE
    image = Image.new('RGBA',(size*2,size*2))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((T.GAP,T.GAP,size*2-T.GAP,size*2-T.GAP),radius=T.RADIUS*4,fill=T.BG_SIDEBAR)
    draw.ellipse((size*.4,size*.25,size*1.6,size*1.45),outline=T.ACCENT,width=T.PAD)
    draw.line((size*.55,size*1.3,size*1.5,size*.4),fill=T.TEXT,width=T.PAD)
    try:
        face = ImageFont.truetype('segoeuib.ttf',T.LOGO_FONT_SIZE*2)
    except OSError:
        face = ImageFont.load_default(size=T.LOGO_FONT_SIZE*2)
    draw.text((size,size*1.7),'PyPhotoEditor',font=face,anchor='mm',fill=T.TEXT)
    return image.resize((size,size),Image.Resampling.LANCZOS)
