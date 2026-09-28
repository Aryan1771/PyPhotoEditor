import statistics
import time
import numpy as np
import pytest
from PIL import Image
from pyphotoeditor.core.brush_effects import EFFECTS
from pyphotoeditor.core.brush import Brush
from pyphotoeditor.core.stroke import StrokeSession
from pyphotoeditor.core.document import Document
from pyphotoeditor.core import image_ops, filters, dithering, segmentation


@pytest.mark.parametrize('key',[k for k,e in EFFECTS.items() if not e.alpha_effect])
def test_effect_alpha_and_outside_footprint(key):
    a = np.random.default_rng(8).integers(0,256,(72,80,4),dtype=np.uint8)
    doc = Document(Image.fromarray(a))
    stroke = StrokeSession(doc,EFFECTS[key],Brush(size=24))
    stroke.move_to((30,30))
    coverage = stroke.coverage.copy()
    stroke.finish()
    b = np.asarray(doc.image)
    np.testing.assert_array_equal(b[...,3],a[...,3])
    np.testing.assert_array_equal(b[coverage==0],a[coverage==0])


@pytest.mark.parametrize('key',['blur','sharpen','pixelate','ordered_dither','noise','emboss','cartoon'])
def test_padded_roi_matches_global_effect(key):
    a = np.random.default_rng(9).integers(0,256,(110,120,4),dtype=np.uint8)
    effect = EFFECTS[key]
    doc = Document(Image.fromarray(a))
    s = StrokeSession(doc,effect,Brush('square',20))
    s.move_to((49,53))
    s.finish()
    expected = effect.fn(a,dict(effect.defaults(),_origin=(0,0)))
    np.testing.assert_array_equal(np.asarray(doc.image)[43:63,39:59],expected[43:63,39:59])


@pytest.mark.parametrize('fn',[image_ops.grayscale,image_ops.invert,image_ops.auto_contrast,filters.gaussian_blur,filters.median_filter,filters.unsharp_mask,filters.sobel_edges,filters.canny_edges,filters.clahe,filters.denoise_tv,dithering.floyd_steinberg,segmentation.kmeans_posterize])
def test_global_effect_alpha(fn):
    a = np.random.default_rng(4).integers(0,256,(16,16,4),dtype=np.uint8)
    result = np.asarray(fn(Image.fromarray(a)))
    np.testing.assert_array_equal(result[...,3],a[...,3])


@pytest.mark.slow
@pytest.mark.parametrize('key',['negative','blur','pixelate'])
def test_12mp_stamp_performance(key):
    doc = Document(Image.new('RGBA',(4000,3000),(80,120,160,255)))
    s = StrokeSession(doc,EFFECTS[key],Brush(size=200))
    timings = []
    for x in range(300,3000,220):
        start = time.perf_counter()
        s.publish(s.stamp((x,1000)))
        timings.append(time.perf_counter()-start)
    median = statistics.median(timings)
    print(f'{key}: {median*1000:.2f} ms median stamp + image patch')
    assert median < .030
    s.cancel()
