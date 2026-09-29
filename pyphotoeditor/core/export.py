"""Atomic, alpha-aware file export; failed writes leave the original intact."""
import os
from pathlib import Path
import tempfile
from PIL import Image


def save_image(image, path):
    path = Path(path).expanduser().absolute()
    suffix = path.suffix.lower()
    formats = {'.png':'PNG','.jpg':'JPEG','.jpeg':'JPEG','.webp':'WEBP',
               '.tif':'TIFF','.tiff':'TIFF'}
    if suffix not in formats:
        raise ValueError('Save as PNG, JPEG, WEBP or TIFF. Use Save As to choose a supported format.')
    if formats[suffix] == 'JPEG':
        background = Image.new('RGBA',image.size,(255,255,255,255))
        image = Image.alpha_composite(background,image.convert('RGBA')).convert('RGB')
    descriptor, temporary = tempfile.mkstemp(prefix='.pyphotoeditor-', suffix=suffix, dir=path.parent)
    os.close(descriptor)
    try:
        image.save(temporary,format=formats[suffix])
        with open(temporary,'r+b') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
