import tkinter as tk
import time
import pytest
from PIL import Image
from pyphotoeditor.ui.app import App


def test_app_build_and_pointer_smoke():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('No display available')
    try:
        app = App(root)
        app.document.load(Image.new('RGBA',(120,100),'white'))
        root.update()
        app.canvas_view.fit_to_window()
        root.update()
        w = app.canvas_view.widget
        x,y = app.canvas_view.image_origin
        x,y = int(x+20),int(y+20)
        w.event_generate('<ButtonPress-1>',x=x,y=y)
        w.event_generate('<B1-Motion>',x=x+30,y=y+30)
        w.event_generate('<ButtonRelease-1>',x=x+30,y=y+30)
        deadline = time.monotonic()+5
        while app.drawing and time.monotonic() < deadline:
            root.update()
            time.sleep(.005)
        assert not app.drawing
        assert len(app.document.history) == 1
        assert 'PyPhotoEditor' in root.title()
    finally:
        root.destroy()
