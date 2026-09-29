import numpy as np
import pytest
from PIL import Image
from pyphotoeditor.core.image_io import load_image
from pyphotoeditor.core.document import Document
from pyphotoeditor.core.brush import Brush
from pyphotoeditor.core.brush_effects import EFFECTS
from pyphotoeditor.core.stroke import StrokeSession
from pyphotoeditor.core.export import save_image


@pytest.mark.parametrize('ext,fmt',[('png','PNG'),('jpg','JPEG'),('webp','WEBP'),('bmp','BMP'),('tiff','TIFF'),('gif','GIF'),('ico','ICO'),('avif','AVIF'),('heic','HEIF'),('heif','HEIF'),('qoi','QOI'),('jp2','JPEG2000')])
def test_open_edit_save_roundtrip(tmp_path,ext,fmt):
    if fmt == 'HEIF':
        pytest.importorskip('pillow_heif').register_heif_opener()
    image = Image.new('RGBA',(64,64),(30,90,160,255))
    path = tmp_path / f'image ü space.{ext}'
    (image.convert('RGB') if fmt == 'JPEG' else image).save(path,format=fmt)
    loaded = load_image(path)
    doc = Document(loaded.image)
    before = doc.image.tobytes()
    s = StrokeSession(doc,EFFECTS['negative'],Brush('square',12))
    s.move_to((24,24));s.finish()
    assert doc.image.tobytes() != before
    output = tmp_path/'edited.png'
    save_image(doc.image,output)
    np.testing.assert_array_equal(np.asarray(load_image(output).image),np.asarray(doc.image))
    doc.undo();assert doc.image.tobytes() == before


def test_svg_import_and_safe_export_path(tmp_path):
    pytest.importorskip('resvg_py')
    path = tmp_path/'drawing.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="24"><rect width="32" height="24" fill="red"/></svg>')
    loaded = load_image(path)
    assert loaded.image.size == (32,24)
    assert loaded.image.getpixel((10,10)) == (255,0,0,255)
    assert loaded.save_path is None


def test_exif_orientation_and_multiframe(tmp_path):
    image = Image.new('RGB',(40,20),'red')
    exif = Image.Exif();exif[274] = 6
    path = tmp_path/'rotated.jpg';image.save(path,exif=exif)
    assert load_image(path).image.size == (20,40)
    path = tmp_path/'animated.gif'
    image.save(path,save_all=True,append_images=[Image.new('RGB',(40,20),'blue')])
    loaded = load_image(path)
    assert loaded.frames == 2
    assert loaded.save_path is None


def test_corrupt_and_missing_image_errors(tmp_path):
    path = tmp_path/'broken.png';path.write_text('not an image')
    with pytest.raises(Exception):load_image(path)
    with pytest.raises(FileNotFoundError):load_image(tmp_path/'missing.png')


def test_raw_dng_import(tmp_path):
    pytest.importorskip('rawpy')
    from pyphotoeditor.diagnostics import create_dng_fixture
    path = tmp_path/'synthetic camera.dng'
    create_dng_fixture(path)
    loaded = load_image(path)
    assert loaded.image.size == (128,96)
    assert loaded.image.mode == 'RGBA'
    assert loaded.save_path is None
