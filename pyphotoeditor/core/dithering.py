"""
dithering
=========
Floyd-Steinberg error-diffusion dithering, implemented directly on a NumPy
array. Kept in its own module (rather than lumped into filters.py) because
it is a distinct algorithm family (halftoning) with its own vectorized
inner loop, so it has a different testing/perf profile than the SciPy /
scikit-image filters.
"""

from __future__ import annotations
from .alpha import preserve_alpha
import numpy as np
from PIL import Image


@preserve_alpha
def floyd_steinberg(img: Image.Image) -> Image.Image:
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    work = gray.copy()
    h, w = work.shape

    for y in range(h):
        for x in range(w):
            old = work[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            err = old - new
            work[y, x] = new
            if x + 1 < w:
                work[y, x + 1] += err * 7 / 16
            if y + 1 < h and x > 0:
                work[y + 1, x - 1] += err * 3 / 16
            if y + 1 < h:
                work[y + 1, x] += err * 5 / 16
            if y + 1 < h and x + 1 < w:
                work[y + 1, x + 1] += err * 1 / 16

    out = (np.clip(work, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, "L").convert("RGBA")
