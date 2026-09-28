"""
image_ops
=========
Basic, "everyday" image operations. These lean on Pillow directly because
Pillow already implements them efficiently and correctly; there is no
benefit to re-deriving them with NumPy. Every function is `Image -> Image`
so `Document.apply()` (see document.py) can call any of them uniformly.
"""

from __future__ import annotations
import numpy as np
from PIL import Image, ImageOps
from skimage import color


def grayscale(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGB"))
    gray = color.rgb2gray(arr)
    out = (gray * 255).astype(np.uint8)
    return Image.fromarray(out, "L").convert("RGBA")


def invert(img: Image.Image) -> Image.Image:
    return ImageOps.invert(img.convert("RGB")).convert("RGBA")


def auto_contrast(img: Image.Image) -> Image.Image:
    return ImageOps.autocontrast(img.convert("RGB")).convert("RGBA")


def flip_horizontal(img: Image.Image) -> Image.Image:
    return ImageOps.mirror(img)


def flip_vertical(img: Image.Image) -> Image.Image:
    return ImageOps.flip(img)


def rotate(img: Image.Image, degrees: float) -> Image.Image:
    return img.rotate(degrees, expand=True, resample=Image.Resampling.BICUBIC)


def resize(img: Image.Image, width: int, height: int) -> Image.Image:
    width = max(1, int(width))
    height = max(1, int(height))
    return img.resize((width, height), Image.Resampling.LANCZOS)


def crop(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    return img.crop(box)
