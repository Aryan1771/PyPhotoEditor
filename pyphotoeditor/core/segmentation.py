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
from skimage.segmentation import watershed
from skimage.feature import canny
from sklearn.cluster import KMeans


def grabcut_foreground(img: Image.Image, rect=None, iterations=5) -> Image.Image:
    """Extract a foreground object locally with OpenCV GrabCut.

    A rectangle gives GrabCut its usual foreground/background initialization;
    with no rectangle, a conservative border/background initialization is used.
    The original RGB values are preserved and only alpha is changed.
    """
    rgba = np.asarray(img.convert("RGBA")).copy()
    rgb = np.ascontiguousarray(rgba[..., :3])
    h, w = rgb.shape[:2]
    if h < 3 or w < 3:
        raise ValueError("Foreground extraction requires an image at least 3×3 pixels.")
    try:
        import cv2
        mask = np.zeros((h, w), np.uint8)
        bg_model, fg_model = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        if rect:
            x1, y1, x2, y2 = map(int, rect)
            x1,x2 = max(0,min(w-1,min(x1,x2))), max(1,min(w,max(x1,x2)))
            y1,y2 = max(0,min(h-1,min(y1,y2))), max(1,min(h,max(y1,y2)))
            if x2 - x1 < 2 or y2 - y1 < 2:
                raise ValueError("Draw a foreground box at least 2×2 pixels wide.")
            cv2.grabCut(rgb, mask, (x1, y1, x2 - x1, y2 - y1), bg_model, fg_model,
                        max(1, int(iterations)), cv2.GC_INIT_WITH_RECT)
        else:
            mask[:] = cv2.GC_PR_FGD
            mask[[0, -1], :] = cv2.GC_BGD
            mask[:, [0, -1]] = cv2.GC_BGD
            inset = max(1, min(h, w) // 30)
            mask[inset:h-inset, inset:w-inset] = cv2.GC_PR_FGD
            cv2.grabCut(rgb, mask, None, bg_model, fg_model, max(1, int(iterations)), cv2.GC_INIT_WITH_MASK)
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except ImportError:
        # Dependency-free-within-the-core fallback: edge-aware watershed from
        # an interior foreground marker and image-border background markers.
        gray = color.rgb2gray(rgb)
        edges = canny(gray, sigma=1.5)
        markers = np.zeros((h, w), np.int32)
        markers[0, :] = markers[-1, :] = markers[:, 0] = markers[:, -1] = 1
        markers[max(1, h//5):max(2, 4*h//5), max(1, w//5):max(2, 4*w//5)] = 2
        labels = watershed(1.0 - edges.astype(np.float32), markers)
        alpha = (labels == 2).astype(np.uint8) * 255
    alpha = ndimage.gaussian_filter(alpha.astype(np.float32), sigma=0.8).clip(0, 255).astype(np.uint8)
    rgba[..., 3] = ((rgba[..., 3].astype(np.uint16) * alpha.astype(np.uint16)) // 255).astype(np.uint8)
    return Image.fromarray(rgba)


def flood_select(img: Image.Image, point, tolerance=24):
    """Return a soft 0..1 contiguous selection matching the sampled color."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    x, y = map(int, point)
    if not (0 <= x < rgb.shape[1] and 0 <= y < rgb.shape[0]):
        raise ValueError("Selection point is outside the image.")
    try:
        import cv2
        sampled = cv2.cvtColor(rgb[y:y+1,x:x+1],cv2.COLOR_RGB2LAB)[0,0].astype(np.float32)
        allowed=np.zeros(rgb.shape[:2],dtype=bool)
        limit=max(0.1,float(tolerance))**2
        # Bounded tiles avoid allocating a full float Lab image for large photos.
        for top in range(0,rgb.shape[0],256):
            for left in range(0,rgb.shape[1],512):
                tile=rgb[top:top+256,left:left+512]
                lab=cv2.cvtColor(tile,cv2.COLOR_RGB2LAB).astype(np.float32)
                delta=lab-sampled
                delta[...,0]*=(100/255)
                allowed[top:top+tile.shape[0],left:left+tile.shape[1]]=np.sum(delta*delta,axis=2)<=limit
    except ImportError:
        sample=color.rgb2lab(rgb[y:y+1,x:x+1].astype(np.float32)/255)[0,0]
        allowed=np.zeros(rgb.shape[:2],dtype=bool)
        for top in range(0,rgb.shape[0],128):
            tile=color.rgb2lab(rgb[top:top+128].astype(np.float32)/255)
            allowed[top:top+tile.shape[0]]=np.sum((tile-sample)**2,axis=2)<=max(.1,float(tolerance))**2
    labels, _ = ndimage.label(allowed)
    component = labels == labels[y, x]
    return ndimage.gaussian_filter(component.astype(np.float32), sigma=0.7).clip(0, 1)


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

    cluster_count = min(n_clusters,len(np.unique(fit_sample,axis=0)))
    km = KMeans(n_clusters=cluster_count, n_init=3, random_state=0)
    km.fit(fit_sample)
    labels = km.predict(pixels)
    out = km.cluster_centers_[labels].reshape(h, w, 3)
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8)).convert("RGBA")


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
    return Image.fromarray(rgba)
