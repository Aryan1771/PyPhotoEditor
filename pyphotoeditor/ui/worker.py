"""Workers never touch Tk. Polling and result delivery run on the Tk thread."""
from queue import Queue, Empty
from threading import Thread, Event
import tkinter as tk
from tkinter import ttk, messagebox
from . import theme as T
from .widgets import RoundedButton


class OperationRunner:
    def __init__(self,app):
        self.app = app
        self.cancel_event = Event()
        self.queue = Queue()

    def start(self,transform,name):
        app = self.app
        if app.busy or app.document.image is None:
            return
        app.active_tool.on_up(app,None)
        snapshot = app.document.image.copy()
        revision = app.document.revision
        self.cancel_event = Event()
        app.busy = True
        self.dialog = tk.Toplevel(app.root)
        self.dialog.title(name)
        self.dialog.transient(app.root)
        tk.Label(self.dialog,text=name+' — working…',fg=T.TEXT,padx=T.PAD,pady=T.PAD).pack()
        self.progress = ttk.Progressbar(self.dialog,mode='indeterminate')
        self.progress.pack(fill='x',padx=T.PAD,pady=T.GAP)
        self.progress.start()
        RoundedButton(self.dialog,text='Cancel',command=self.cancel).pack(padx=T.PAD,pady=T.GAP)
        self.dialog.protocol('WM_DELETE_WINDOW',self.cancel)
        def work():
            try:
                result = transform(snapshot)
                self.queue.put((result,None))
            except Exception as exc:
                self.queue.put((None,str(exc)))
        Thread(target=work,daemon=True,name='image-operation').start()
        app.root.after(40,lambda:self.poll(revision,name))

    def cancel(self):
        self.cancel_event.set()
        self.dialog.withdraw()
        self.app.status('Cancelled; waiting for the image library to finish its current operation.')

    def poll(self,revision,name):
        try:
            result,error = self.queue.get_nowait()
        except Empty:
            self.app.root.after(40,lambda:self.poll(revision,name))
            return
        self.progress.stop()
        self.dialog.destroy()
        app = self.app
        app.busy = False
        if self.cancel_event.is_set():
            app.status('Operation cancelled; image unchanged.')
        elif app.document.revision != revision:
            app.status('Discarded result because the document changed.')
        elif error:
            messagebox.showerror('Image operation failed',error,parent=app.root)
        else:
            app.document.apply(lambda _:result,name)
            app.canvas_view.render()
            app.refresh_history()
            app.status(name+' complete.')
