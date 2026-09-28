"""
filters
=======
Filters backed by SciPy and scikit-image. Each function takes/returns a
Pillow `Image` so they compose transparently with `Document.apply()` and
with `image_ops` -- callers never need to know which library did the work.

Internally, helper `_from_rgb_float` / `_to_rgb_array` centralize the
uint8 <-> float[0,1] <-> PIL conversions so each filter body stays focused
on the actual algorithm (functional cohesion).
"""

from __future__ import annotations
from .alpha import preserve_alpha
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from skimage import color, exposure, filters as skfilters, feature, restoration


def _to_rgb_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"))


def _from_rgb_array(arr: np.ndarray) -> Image.Image:
    if arr.dtype != np.uint8:
        arr = np.clip(arr * 255 if arr.max() <= 1.0 else arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


@preserve_alpha
def gaussian_blur(img: Image.Image, sigma: float = 2.0) -> Image.Image:
    arr = _to_rgb_array(img)
    out = ndimage.gaussian_filter(arr, sigma=(sigma, sigma, 0))
    return _from_rgb_array(out)


@preserve_alpha
def median_filter(img: Image.Image, size: int = 3) -> Image.Image:
    arr = _to_rgb_array(img)
    out = ndimage.median_filter(arr, size=(size, size, 1))
    return _from_rgb_array(out)


@preserve_alpha
def unsharp_mask(img: Image.Image, radius: float = 2, percent: int = 160, threshold: int = 3) -> Image.Image:
    return img.convert("RGB").filter(
        ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
    ).convert("RGBA")


@preserve_alpha
def sobel_edges(img: Image.Image) -> Image.Image:
    arr = _to_rgb_array(img)
    gray = color.rgb2gray(arr)
    sx = skfilters.sobel_h(gray)
    sy = skfilters.sobel_v(gray)
    mag = np.sqrt(sx * sx + sy * sy)
    out = 1 - np.clip(mag * 4, 0, 1)
    return _from_rgb_array(np.repeat(out[..., None], 3, axis=2))


@preserve_alpha
def canny_edges(img: Image.Image, sigma: float = 1.4) -> Image.Image:
    arr = _to_rgb_array(img)
    gray = color.rgb2gray(arr)
    edges = feature.canny(gray, sigma=sigma)
    out = np.where(edges[..., None], 255, 0).astype(np.uint8).repeat(3, axis=2)
    return _from_rgb_array(out)


@preserve_alpha
def clahe(img: Image.Image, clip_limit: float = 0.03) -> Image.Image:
    arr = _to_rgb_array(img) / 255.0
    lab = color.rgb2lab(arr)
    l_channel = exposure.equalize_adapthist(lab[..., 0] / 100.0, clip_limit=clip_limit) * 100
    lab[..., 0] = l_channel
    out = color.lab2rgb(lab)
    return _from_rgb_array(out)


@preserve_alpha
def denoise_tv(img: Image.Image, weight: float = 0.08) -> Image.Image:
    arr = _to_rgb_array(img) / 255.0
    out = restoration.denoise_tv_chambolle(arr, weight=weight, channel_axis=-1)
    return _from_rgb_array(out)
