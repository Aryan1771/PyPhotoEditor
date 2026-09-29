"""Explicit packaged-runtime smoke test. Only used with --self-test DIRECTORY."""
import json
from pathlib import Path
import time
import traceback
import numpy as np
from PIL import Image


def run_self_test(directory):
    output = Path(directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'ok':False, 'checks':[]}
    root = None
    try:
        from .core.image_io import load_image
        from .core.document import Document
        from .core.brush import Brush
        from .core.brush_effects import EFFECTS
        from .core.stroke import StrokeSession
        from .core.export import save_image
        from .core import filters, segmentation
        from pillow_heif import register_heif_opener
        import rawpy
        import resvg_py
        register_heif_opener()
        sample = Image.new('RGBA', (96, 64), (30, 90, 160, 255))
        formats = [('png','PNG'),('jpg','JPEG'),('jpeg','JPEG'),('webp','WEBP'),
                   ('bmp','BMP'),('tiff','TIFF'),('gif','GIF'),('ico','ICO'),
                   ('avif','AVIF'),('heic','HEIF'),('heif','HEIF'),('qoi','QOI'),('jp2','JPEG2000')]
        for ext, fmt in formats:
            path = output / f'image sample ü.{ext}'
            source = sample.convert('RGB') if fmt == 'JPEG' else sample
            source.save(path, format=fmt)
            loaded = load_image(path)
            doc = Document(loaded.image)
            before = doc.image.tobytes()
            stroke = StrokeSession(doc, EFFECTS['negative'], Brush('square', 16))
            stroke.move_to((20,20)); stroke.finish()
            assert doc.image.tobytes() != before, ext
            edited = output / f'edited-{ext}.png'
            save_image(doc.image, edited)
            assert Image.open(edited).tobytes() == doc.image.tobytes(), ext
            doc.undo(); assert doc.image.tobytes() == before
            doc.redo()
            report['checks'].append(f'{ext}: decode, edit, export, undo/redo')
        svg = output/'image sample ü.svg'
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="96" height="64"><rect width="96" height="64" fill="#1e5aa0"/></svg>',encoding='utf-8')
        assert load_image(svg).image.getpixel((20,20)) == (30,90,160,255)
        report['checks'].append('SVG rasterization')
        dng = output/'synthetic camera.dng'
        create_dng_fixture(dng)
        raw_image = load_image(dng)
        assert raw_image.image.size == (128,96) and raw_image.save_path is None
        save_image(raw_image.image,output/'decoded-raw.png')
        report['checks'].append('DNG camera RAW decode and PNG export: '+str(rawpy.libraw_version))
        alpha = Image.new('RGBA',(64,64),(20,80,140,87))
        for effect in (filters.gaussian_blur,filters.clahe,filters.denoise_tv,segmentation.kmeans_posterize):
            result = effect(alpha)
            assert np.all(np.asarray(result)[...,3] == 87)
            report['checks'].append(effect.__name__+' bundled dependencies')
        import tkinter as tk
        from .ui.app import App
        root = tk.Tk()
        root.withdraw()
        app = App(root)
        errors = []
        root.report_callback_exception = lambda *args:errors.append(str(args))
        assert app.open_image(str(output/'image sample ü.png'))
        app.select_tool('negative')
        app.active_tool.on_down(app,(40,30))
        app.active_tool.on_move(app,(60,30))
        app.active_tool.on_up(app,(60,30))
        deadline = time.monotonic()+20
        while app.drawing and time.monotonic() < deadline:
            root.update(); time.sleep(.005)
        assert not app.drawing and not errors, errors
        assert len(app.document.history) == 1
        app.document.filepath = str(output/'ui-edited.png')
        app.save_image()
        assert Image.open(output/'ui-edited.png').getpixel((50,30))[:3] == (225,165,95)
        report['checks'].append('Tk open → asynchronous brush edit → save PNG')
        app._apply(filters.gaussian_blur)
        while app.busy and time.monotonic() < deadline:
            root.update(); time.sleep(.005)
        assert not app.busy and not errors, errors
        report['checks'].append('Tk background filter worker')
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if root is not None:
            root.destroy()
        (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if report['ok'] else 1


def create_dng_fixture(path):
    """Small synthetic Bayer DNG exercises the bundled LibRaw binary end to end."""
    import tifffile
    ramp = np.linspace(512,3500,128*96,dtype=np.uint16).reshape(96,128)
    tags = [(50706,'B',4,(1,4,0,0),False), (50707,'B',4,(1,1,0,0),False),
            (50708,'s',0,'PyPhotoEditor synthetic',False),
            (33421,'H',2,(2,2),False), (33422,'B',4,(0,1,1,2),False),
            (50714,'H',1,0,False), (50717,'I',1,4095,False),
            (50721,'2i',9,(1,1,0,1,0,1,0,1,1,1,0,1,0,1,0,1,1,1),False),
            (50728,'2I',3,(1,1,1,1,1,1),False), (50778,'H',1,21,False)]
    tifffile.imwrite(path,ramp,photometric=32803,metadata=None,extratags=tags)
