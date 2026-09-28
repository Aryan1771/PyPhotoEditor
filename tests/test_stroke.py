import numpy as np
from PIL import Image
from pyphotoeditor.core.document import Document, PatchCommand
from pyphotoeditor.core.brush import Brush
from pyphotoeditor.core.stroke import StrokeSession
from pyphotoeditor.core.brush_effects import EFFECTS


def test_crossing_stroke_uses_union_and_one_patch():
    rng = np.random.default_rng(42)
    original = rng.integers(0,256,(400,600,4),dtype=np.uint8)
    doc = Document(Image.fromarray(original))
    s = StrokeSession(doc,EFFECTS['negative'],Brush(size=20))
    for p in [(60,60),(120,120),(60,120),(120,60),(60,60)]:
        s.move_to(p)
    coverage = s.coverage.copy()
    s.finish()
    expected = original.copy()
    expected[coverage > 0,:3] = 255-original[coverage > 0,:3]
    np.testing.assert_array_equal(np.asarray(doc.image),expected)
    assert len(doc.history) == 1
    assert isinstance(doc.history[0],PatchCommand)
    assert doc.history[0].nbytes < original.nbytes*.1
    assert doc.undo()
    np.testing.assert_array_equal(np.asarray(doc.image),original)
    assert doc.redo()
    np.testing.assert_array_equal(np.asarray(doc.image),expected)


def test_footprints():
    assert Brush('square',20).footprint()[0,0] == 1
    assert Brush('circle',20).footprint()[0,0] == 0
    mask = Brush(size=20,hardness=30).footprint()
    assert np.any((mask>0)&(mask<1))
    assert mask.dtype == np.float32


def test_selection_strength_and_buildup():
    doc = Document(Image.new('RGBA',(40,40),(20,40,60,128)))
    doc.selection = np.zeros((40,40),np.float32)
    doc.selection[:,:20] = .5
    s = StrokeSession(doc,EFFECTS['negative'],Brush('square',20,strength=50))
    s.move_to((20,20)); s.move_to((20,20)); s.finish()
    a = np.asarray(doc.image)
    assert tuple(a[20,15]) == (74,84,94,128)
    assert tuple(a[20,25]) == (20,40,60,128)


def test_budget_branching_and_failure_atomicity():
    doc = Document(Image.new('RGBA',(10,10)),memory_budget=1700)
    for value in (10,20,30):
        doc.apply(lambda im,v=value:Image.new('RGBA',im.size,(v,v,v,255)))
    assert doc.history_bytes <= doc.memory_budget
    assert len(doc.history) == 2
    doc.undo()
    doc.apply(lambda im:Image.new('RGBA',im.size,'red'))
    assert not doc.redo()
    before = doc.image.tobytes()
    try:
        doc.apply(lambda im:1/0)
    except ZeroDivisionError:
        pass
    assert doc.image.tobytes() == before
