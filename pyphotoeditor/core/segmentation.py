"""
segmentation
============
Higher-level, "understand the image" operations built on scikit-learn
(clustering) and scikit-image + SciPy (morphology / connected components).
Grouped separately from `filters.py` because these operate on *regions*
of the image rather than per-pixel neighborhoods -- a different concern,
so it gets its own module (functional cohesion).
"""

from __future__ import annotations
from .alpha import preserve_alpha
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import color, filters as skfilters, morphology
from sklearn.cluster import KMeans


@preserve_alpha
def kmeans_posterize(img: Image.Image, n_clusters: int = 8, sample_cap: int = 50_000) -> Image.Image:
    """Reduce the image to `n_clusters` dominant colors via K-Means."""
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    h, w, _ = arr.shape
    pixels = arr.reshape(-1, 3)

    if len(pixels) > sample_cap:
        idx = np.linspace(0, len(pixels) - 1, sample_cap).astype(int)
        fit_sample = pixels[idx]
    else:
        fit_sample = pixels

    km = KMeans(n_clusters=min(n_clusters,len(fit_sample)), n_init=3, random_state=0)
    km.fit(fit_sample)
    labels = km.predict(pixels)
    out = km.cluster_centers_[labels].reshape(h, w, 3)
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def rotoscope(img: Image.Image) -> Image.Image:
    """
    Educational automatic foreground extraction:
      1. Otsu threshold on grayscale creates a foreground candidate.
      2. Morphological cleanup (remove small objects, close, fill holes).
      3. Keep only the largest connected component.
      4. Feather the mask into a soft alpha channel and composite it back.

    This is intentionally a lightweight approximation, not a production
    rotoscoping/matting pipeline.
    """
    rgb = np.asarray(img.convert("RGB"))
    gray = color.rgb2gray(rgb)

    threshold = skfilters.threshold_otsu(gray)
    candidate = gray > threshold
    candidate = morphology.remove_small_objects(
        candidate, min_size=max(64, rgb.shape[0] * rgb.shape[1] // 1000)
    )
    candidate = morphology.binary_closing(candidate, morphology.disk(4))
    candidate = ndimage.binary_fill_holes(candidate)

    labels, count = ndimage.label(candidate)
    if count:
        sizes = ndimage.sum(candidate, labels, range(1, count + 1))
        keep = 1 + int(np.argmax(sizes))
        candidate = labels == keep

    alpha = ndimage.gaussian_filter(candidate.astype(np.float32), sigma=2)
    alpha = np.clip(alpha, 0, 1)
    rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")
