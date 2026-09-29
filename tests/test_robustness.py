import numpy as np
import pytest
from PIL import Image
from pyphotoeditor.core.document import Document
from pyphotoeditor.core.export import save_image
from pyphotoeditor.core.image_ops import validate_dimensions


def test_dirty_state_survives_branching_eviction_and_save():
    doc = Document(Image.new('RGBA',(10,10),'white'),memory_budget=800)
    assert not doc.dirty
    doc.apply(lambda im:Image.new('RGBA',im.size,'red'))
    assert doc.dirty
    doc.mark_saved();assert not doc.dirty
    doc.undo();assert doc.dirty
    doc.redo();assert not doc.dirty
    doc.apply(lambda im:Image.new('RGBA',im.size,'blue'))
    assert doc.dirty
    doc.undo();assert not doc.dirty
    doc.apply(lambda im:Image.new('RGBA',im.size,'green'))
    assert doc.dirty and not doc.redo()


@pytest.mark.parametrize('dimensions',[('','2'),('x','3'),('1.5','3'),('0','3'),('-1','3'),('32769','2'),('20000','20000'),('inf','1')])
def test_invalid_dimensions_fail_cleanly(dimensions):
    with pytest.raises(ValueError):validate_dimensions(*dimensions)


def test_failed_export_never_corrupts_original(tmp_path,monkeypatch):
    path = tmp_path/'original.png'
    image = Image.new('RGBA',(20,20),'blue')
    image.save(path)
    original = path.read_bytes()
    def partial_write(self,filename,**kwargs):
        with open(filename,'wb') as stream:stream.write(b'incomplete')
        raise OSError('Disk write failed')
    monkeypatch.setattr(Image.Image,'save',partial_write)
    with pytest.raises(OSError):save_image(image,path)
    assert path.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ['original.png']


def test_rgba_roundtrip_and_jpeg_white_flatten(tmp_path):
    image = Image.new('RGBA',(10,10),(10,20,30,0))
    for suffix in ('png','webp','tiff'):
        path = tmp_path/f'rgba.{suffix}'
        save_image(image,path)
        assert Image.open(path).convert('RGBA').getpixel((0,0))[3] == 0
    path = tmp_path/'flatten.jpg';save_image(image,path)
    assert Image.open(path).getpixel((0,0)) == (255,255,255)
