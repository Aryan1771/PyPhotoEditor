import tkinter as tk
import time
import pytest
from PIL import Image
from pyphotoeditor.ui.app import App


@pytest.fixture(scope='module')
def desktop_app():
    # One Tcl interpreter per process avoids Windows Store Tk reinitialization
    # failures; individual tests reset document/tool state below.
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f'Cannot initialize Tk display: {exc}')
    errors = []
    root.report_callback_exception = lambda *args:errors.append(args)
    app = App(root)
    root.update()
    yield app
    assert not errors,errors
    root.destroy()


@pytest.fixture
def application(desktop_app):
    app = desktop_app
    app.document.load(Image.new('RGBA',(160,120),(100,150,200,255)))
    app.brush_size = 20
    app.select_tool('brush')
    app.root.geometry('1400x900')
    app.refresh_history()
    app.root.update()
    return app


def test_app_build_and_pointer_smoke(application):
    app = application
    app.document.load(Image.new('RGBA',(120,100),'white'))
    app.canvas_view.fit_to_window()
    app.root.update()
    w = app.canvas_view.widget
    x,y = app.canvas_view.image_origin
    x,y = int(x+20),int(y+20)
    w.event_generate('<ButtonPress-1>',x=x,y=y)
    w.event_generate('<B1-Motion>',x=x+30,y=y+30)
    w.event_generate('<ButtonRelease-1>',x=x+30,y=y+30)
    settle(app)
    assert len(app.document.history) == 1
    assert 'PyPhotoEditor' in app.root.title()


def settle(app):
    deadline = time.monotonic()+10
    while (app.drawing or app.busy) and time.monotonic() < deadline:
        app.root.update()
        time.sleep(.005)
    app.root.update()
    assert not app.drawing and not app.busy


def test_rapid_strokes_and_deferred_undo(application):
    app = application
    app.select_tool('negative')
    tool = app.active_tool
    tool.on_down(app,(30,30));tool.on_move(app,(70,30));tool.on_up(app,(70,30))
    tool.on_down(app,(30,80));tool.on_move(app,(70,80));tool.on_up(app,(70,80))
    settle(app)
    assert len(app.document.history) == 2
    assert app.document.image.getpixel((50,30))[:3] == (155,105,55)
    assert app.document.image.getpixel((50,80))[:3] == (155,105,55)
    tool.on_down(app,(110,50));tool.on_up(app,(110,50));app.undo()
    settle(app)
    # Deferred undo is scheduled after the last stroke's completion.
    end = time.monotonic()+.1
    while time.monotonic() < end:
        app.root.update();time.sleep(.005)
    assert app.document.history_index == 2
    assert app.document.image.getpixel((110,50))[:3] == (100,150,200)


def test_background_stroke_preparation_and_minimum_layout(application):
    app = application
    app.document.load(Image.new('RGBA',(160,120),'white'))
    app.select_tool('background_eraser')
    app.root.geometry('1000x700')
    app.root.update()
    assert app.options.winfo_reqwidth() <= app.root.winfo_width()
    app.active_tool.on_down(app,(30,30))
    app.active_tool.on_move(app,(90,30))
    app.active_tool.on_up(app,(90,30))
    settle(app)
    assert app.document.image.getpixel((60,30))[3] == 0
    assert len(app.document.history) == 1


def test_worker_cancel_stale_and_main_thread_delivery(application):
    from threading import Event, get_ident
    app = application
    before = app.document.image.tobytes()
    gate = Event()
    worker_threads = []
    main = get_ident()
    def operation(image):
        worker_threads.append(get_ident())
        gate.wait(3)
        return Image.new('RGBA',image.size,'red')
    app.runner.start(operation,'Test cancellation')
    app.runner.cancel();gate.set();settle(app)
    assert app.document.image.tobytes() == before
    assert not app.document.history
    assert worker_threads[0] != main
    gate.clear()
    app.runner.start(operation,'Test stale result')
    app.document.new(20,20,'blue')
    gate.set();settle(app)
    assert app.document.size == (20,20)
    assert app.document.image.getpixel((0,0)) == (0,0,255,255)
    delivered = []
    app.runner.submit(lambda:42,'Thread delivery',lambda result:delivered.append((result,get_ident())),show_progress=False)
    settle(app)
    assert delivered == [(42,main)]


def test_all_registered_tool_controls_build(application):
    app = application
    for name in app.tools:
        app.select_tool(name)
        app.root.update()
        assert app.active_tool.name == name


@pytest.mark.slow
def test_12mp_pointer_handlers_return_promptly(application):
    app = application
    app.document.load(Image.new('RGBA',(4000,3000),(20,80,140,255)))
    app.select_tool('negative')
    app.brush_size = 200
    timings = []
    for fn in [lambda:app.active_tool.on_down(app,(500,500)),lambda:app.active_tool.on_move(app,(2500,1500)),lambda:app.active_tool.on_up(app,(2500,1500))]:
        start = time.perf_counter();fn();timings.append(time.perf_counter()-start)
    settle(app)
    print('12 MP pointer handlers (ms):',[round(t*1000,2) for t in timings])
    assert max(timings) < .030
    assert len(app.document.history) == 1


def test_open_save_failures_and_discard_cancel(application,tmp_path,monkeypatch):
    from pyphotoeditor.ui import app as module
    app = application
    errors = []
    monkeypatch.setattr(module.messagebox,'showerror',lambda *a,**kw:errors.append(a))
    app.document.apply(lambda image:Image.new('RGBA',image.size,'red'),'Red')
    before = app.document.image.tobytes()
    app.document.filepath = str(tmp_path/'existing.png')
    assert not app.open_image(str(tmp_path/'missing.png'))
    assert app.document.image.tobytes() == before
    target = tmp_path/'blue.png';Image.new('RGBA',(80,60),'blue').save(target)
    monkeypatch.setattr(module.messagebox,'askyesnocancel',lambda *a,**kw:None)
    assert not app.open_image(str(target))
    assert app.document.image.tobytes() == before
    monkeypatch.setattr(module,'export_image',lambda *a:(_ for _ in ()).throw(OSError('Disk full')))
    old_path = app.document.filepath
    monkeypatch.setattr(module.filedialog,'asksaveasfilename',lambda **kw:str(tmp_path/'new.png'))
    assert not app.save_as()
    assert app.document.filepath == old_path and app.document.dirty
    assert errors


def test_cancelled_save_does_not_allow_document_replacement(application,tmp_path,monkeypatch):
    from pyphotoeditor.ui import app as module
    app = application
    app.document.apply(lambda im:Image.new('RGBA',im.size,'green'))
    app.document.filepath = None
    before = app.document.image.tobytes()
    monkeypatch.setattr(module.messagebox,'askyesnocancel',lambda *a,**kw:True)
    monkeypatch.setattr(module.filedialog,'asksaveasfilename',lambda **kw:'')
    path = tmp_path/'open.png';Image.new('RGBA',(20,20),'blue').save(path)
    assert not app.open_image(str(path))
    assert app.document.image.tobytes() == before


def test_successful_save_clears_dirty_marker(application,tmp_path):
    app = application
    app.document.apply(lambda im:Image.new('RGBA',im.size,'green'))
    path = tmp_path/'saved ü image.png'
    assert app._save_to(str(path))
    assert not app.document.dirty
    assert not app.root.title().startswith('*')
    assert Image.open(path).getpixel((0,0)) == (0,128,0,255)


def test_invalid_worker_result_is_reported_and_document_unchanged(application,monkeypatch):
    from pyphotoeditor.ui import worker
    app = application
    before = app.document.image.tobytes()
    errors = []
    monkeypatch.setattr(worker.messagebox,'showerror',lambda *a,**kw:errors.append(a))
    app.runner.start(lambda image:None,'Invalid plugin result')
    settle(app)
    assert errors and app.document.image.tobytes() == before
