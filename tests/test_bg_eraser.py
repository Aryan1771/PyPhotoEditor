import numpy as np
from PIL import Image
from pyphotoeditor.core.brush import Brush
from pyphotoeditor.core.stroke import StrokeSession
from pyphotoeditor.core.document import Document
from pyphotoeditor.core.brush_effects import EFFECTS
from pyphotoeditor.core.bg_eraser import lab_distance, alpha_factor
from pyphotoeditor.core.export import save_image


def erase(doc,points,**params):
    s = StrokeSession(doc,EFFECTS['background_eraser'],Brush('square',5),params=params)
    for point in points:
        s.move_to(point)
    s.finish()


def test_white_black_and_connected_island():
    a = np.full((45,45,4),255,np.uint8)
    a[12:33,12:33,:3] = 0
    a[18:27,18:27,:3] = 255
    doc = Document(Image.fromarray(a))
    erase(doc,[(3,22),(40,22)],tolerance=20,softness=0)
    result = np.asarray(doc.image)
    assert result[22,3,3] == 0
    assert result[22,15,3] == 255
    assert result[22,22,3] == 255
    doc = Document(Image.fromarray(a))
    erase(doc,[(3,22),(40,22)],limits='Discontiguous',tolerance=20,softness=0)
    assert np.asarray(doc.image)[22,22,3] == 0


def test_soft_edge_defringe_alpha_never_increases():
    a = np.full((10,10,4),255,np.uint8)
    a[...,:3] = (230,230,230)
    doc = Document(Image.fromarray(a))
    erase(doc,[(5,5)],limits='Discontiguous',tolerance=20,softness=20,defringe=True)
    pixel = np.asarray(doc.image)[5,5]
    assert 0 < pixel[3] < 255
    assert pixel[0] < 230
    before = np.asarray(doc.image).copy()
    erase(doc,[(5,5)],limits='Discontiguous',tolerance=20,softness=20)
    assert np.all(np.asarray(doc.image)[...,3] <= before[...,3])


def test_sampling_restore_and_resize():
    doc = Document(Image.new('RGBA',(30,30),(100,150,200,180)))
    original = doc.image.tobytes()
    erase(doc,[(15,15)],sampling='Sample at stroke start',tolerance=10)
    assert doc.image.getpixel((15,15))[3] == 0
    s = StrokeSession(doc,EFFECTS['restore'],Brush('square',5))
    s.move_to((15,15));s.finish()
    assert doc.image.tobytes() == original
    doc.apply(lambda im:im.resize((15,15)))
    assert not doc.can_restore
    doc.undo()
    assert doc.can_restore


def test_exports(tmp_path):
    image = Image.new('RGBA',(10,10),(0,0,0,0))
    for suffix in ('png','webp','tiff'):
        path = tmp_path/('test.'+suffix)
        save_image(image,path)
        assert Image.open(path).convert('RGBA').getpixel((0,0))[3] == 0
    path = tmp_path/'test.jpg'
    save_image(image,path)
    assert Image.open(path).getpixel((0,0)) == (255,255,255)
