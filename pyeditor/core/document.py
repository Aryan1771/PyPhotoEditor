"""
Document
========
Holds the state of a single open image: the current pixels, the original
(for "reset"), and the undo/redo history. This class knows nothing about
Tkinter, dialogs or drawing tools -- it is a plain state container that the
UI drives. That separation is what lets `core` be tested/reused without a
GUI at all.
"""

from __future__ import annotations
from typing import Callable, Optional
from PIL import Image

MAX_HISTORY = 30


class Document:
    def __init__(self, image: Optional[Image.Image] = None):
        self.filepath: Optional[str] = None
        self.image: Optional[Image.Image] = image
        self.original: Optional[Image.Image] = image.copy() if image else None
        self._undo: list[Image.Image] = []
        self._redo: list[Image.Image] = []

    # ---- lifecycle -------------------------------------------------
    def load(self, image: Image.Image, filepath: Optional[str] = None) -> None:
        self.image = image.convert("RGBA")
        self.original = self.image.copy()
        self.filepath = filepath
        self._undo.clear()
        self._redo.clear()

    def new(self, width: int, height: int, color="white") -> None:
        self.load(Image.new("RGBA", (max(1, width), max(1, height)), color))
        self.filepath = None

    # ---- undo / redo -------------------------------------------------
    def push_undo(self) -> None:
        if self.image is None:
            return
        self._undo.append(self.image.copy())
        if len(self._undo) > MAX_HISTORY:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.image.copy())
        self.image = self._undo.pop()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.image.copy())
        self.image = self._redo.pop()
        return True

    def reset_to_original(self) -> None:
        if self.original is None:
            return
        self.push_undo()
        self.image = self.original.copy()

    # ---- applying a transform with automatic undo tracking ----------
    def apply(self, transform: Callable[[Image.Image], Image.Image]) -> None:
        """Run a pure `Image -> Image` function and record undo history.

        Every filter/operation in `image_ops`, `filters`, `dithering` and
        `segmentation` matches this `Image -> Image` signature, so the UI
        never needs a special case per-effect -- it just calls
        `document.apply(image_ops.grayscale)`.
        """
        if self.image is None:
            return
        self.push_undo()
        self.image = transform(self.image)

    @property
    def size(self):
        return self.image.size if self.image else (0, 0)
