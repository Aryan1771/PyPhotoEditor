import numpy as np
from PIL import Image

from pyphotoeditor.core import drawing, segmentation
from pyphotoeditor.core import Document
from pyphotoeditor.core.brush import Brush
from pyphotoeditor.core.brush_effects import EFFECTS
from pyphotoeditor.core.stroke import StrokeSession


def test_gradient_linear_and_radial_are_bounded_and_alpha_safe():
    image=Image.new('RGBA',(8,6),(20,30,40,255))
    horizontal=drawing.gradient(image,(1,1,7,5),(0,0,0,255),(255,0,0,255),'linear','horizontal')
    assert horizontal.getpixel((0,2))[:3] == (20,30,40)
    assert horizontal.getpixel((2,2))[0] < horizontal.getpixel((6,2))[0]
    assert horizontal.getpixel((2,2))[3] == 255
    radial=drawing.gradient(image,(0,0,8,6),(0,0,0,255),(255,255,255,255),'radial')
    assert radial.getpixel((4,3))[0] < radial.getpixel((0,0))[0]


def test_symbol_stamp_clips_to_document_and_preserves_alpha():
    base=Image.new('RGBA',(12,12),(255,255,255,255))
    icon=Image.new('RGBA',(7,7),(220,10,20,180))
    result=drawing.stamp(base,icon,(0,0),8)
    assert result.size == base.size
    assert result.getpixel((0,0))[0] > 200
    assert result.getpixel((0,0))[3] == 255
    assert result.getpixel((11,11)) == base.getpixel((11,11))


def test_magic_wand_selects_only_connected_color_component():
    pixels=np.zeros((12,16,3),dtype=np.uint8)
    pixels[:]=(0,0,0); pixels[2:6,2:6]=(255,0,0); pixels[7:11,10:14]=(255,0,0)
    mask=segmentation.flood_select(Image.fromarray(pixels),(3,3),tolerance=1)
    assert mask[3,3] > .9 and mask[8,11] < .1


def test_grabcut_runs_offline_and_retains_foreground_pixels():
    image=Image.new('RGBA',(48,48),(15,90,180,255))
    for y in range(14,35):
        for x in range(16,33): image.putpixel((x,y),(230,40,30,255))
    result=segmentation.grabcut_foreground(image,(8,8,40,40),iterations=2)
    assert result.getpixel((24,24))[:3] == (230,40,30)
    assert result.getpixel((24,24))[3] > result.getpixel((3,3))[3]


def test_lasso_selection_clips_stroke_coverage():
    document=Document(Image.new('RGBA',(16,16),'white'))
    document.selection=np.zeros((16,16),dtype=np.float32)
    document.selection[6:10,6:10]=1
    stroke=StrokeSession(document,EFFECTS['paint'],Brush('circle',14,100,100),params={'color':(255,0,0,255)})
    stroke.stamp((8,8)); stroke.publish(stroke.dirty); stroke.finish()
    assert document.image.getpixel((8,8))[:3] == (255,0,0)
    assert document.image.getpixel((2,2))[:3] == (255,255,255)
