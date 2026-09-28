"""Display-independent document and memory-budgeted command history."""
from dataclasses import dataclass
import numpy as np
from PIL import Image


@dataclass
class PatchCommand:
    bbox: tuple
    before: np.ndarray
    after: np.ndarray
    name: str = 'Brush stroke'

    @property
    def nbytes(self):
        return self.before.nbytes + self.after.nbytes

    def undo(self, document):
        document.image.paste(Image.fromarray(self.before), self.bbox[:2])

    def redo(self, document):
        document.image.paste(Image.fromarray(self.after), self.bbox[:2])


@dataclass
class SnapshotCommand:
    before: Image.Image
    after: Image.Image
    name: str = 'Image operation'

    @property
    def nbytes(self):
        return (self.before.width*self.before.height + self.after.width*self.after.height)*4

    def undo(self, document):
        document.image = self.before.copy()
        document.selection = None

    def redo(self, document):
        document.image = self.after.copy()
        document.selection = None


class Document:
    def __init__(self, image=None, memory_budget=512*1024*1024):
        self.filepath = None
        self.image = None
        self.original = None
        self.selection = None
        self.memory_budget = max(0, int(memory_budget))
        self.history = []
        self.history_index = 0
        self.revision = 0
        self._pending = None
        if image is not None:
            self.load(image)

    def load(self, image, filepath=None):
        self.image = image.convert('RGBA')
        self.original = self.image.copy()
        self.filepath = filepath
        self.selection = None
        self.history.clear()
        self.history_index = 0
        self._pending = None
        self.revision += 1

    def new(self, width, height, color='white'):
        self.load(Image.new('RGBA',(max(1,width),max(1,height)),color))

    @property
    def size(self):
        return self.image.size if self.image is not None else (0,0)

    @property
    def history_bytes(self):
        return sum(c.nbytes for c in self.history)

    @property
    def can_restore(self):
        return self.original is not None and self.size == self.original.size

    def record(self, command):
        del self.history[self.history_index:]
        self.history.append(command)
        self.history_index = len(self.history)
        while self.history and self.history_bytes > self.memory_budget:
            self.history.pop(0)
            self.history_index -= 1
        self.revision += 1

    def push_undo(self):
        """Compatibility for older tools; finalized before the next history action."""
        self.finish_pending()
        if self.image is not None:
            self._pending = self.image.copy()

    def finish_pending(self):
        if self._pending is not None:
            before, self._pending = self._pending, None
            self.record(SnapshotCommand(before,self.image.copy()))

    def undo(self):
        self.finish_pending()
        if not self.history_index:
            return False
        self.history_index -= 1
        self.history[self.history_index].undo(self)
        self.revision += 1
        return True

    def redo(self):
        self.finish_pending()
        if self.history_index == len(self.history):
            return False
        self.history[self.history_index].redo(self)
        self.history_index += 1
        self.revision += 1
        return True

    def jump_to(self, index):
        index = max(0,min(len(self.history),int(index)))
        while self.history_index > index:
            self.undo()
        while self.history_index < index:
            self.redo()

    def apply(self, transform, name=None):
        if self.image is None:
            return
        self.finish_pending()
        before = self.image.copy()
        after = transform(before.copy()).convert('RGBA')
        self.image = after
        if before.size != after.size:
            self.selection = None
        self.record(SnapshotCommand(before,after.copy(),name or getattr(transform,'__name__','Image operation').replace('_',' ').title()))

    def reset_to_original(self):
        if self.original is not None:
            self.apply(lambda _:self.original.copy(),'Reset to original')
