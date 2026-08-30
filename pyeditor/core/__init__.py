"""
core
====
Everything in this package is pure image-processing logic:

    - document.py     Document/undo-redo state container
    - image_ops.py     basic Pillow-based transforms (grayscale, rotate, ...)
    - filters.py        SciPy / scikit-image filters (blur, edges, CLAHE, ...)
    - dithering.py       NumPy Floyd-Steinberg dithering
    - segmentation.py    scikit-learn / scikit-image (K-Means, rotoscope)

No module in this package imports tkinter. Every public function takes a
PIL.Image.Image (or plain arguments) and returns a PIL.Image.Image, so the
UI layer can compose them without knowing how they work internally
(functional cohesion + a single, narrow contract between layers).
"""

from .document import Document
from . import image_ops
from . import filters
from . import dithering
from . import segmentation

__all__ = [
    "Document",
    "image_ops",
    "filters",
    "dithering",
    "segmentation",
]
