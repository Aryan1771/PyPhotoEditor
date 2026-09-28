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
        snapshot = app.document.image.copy()
        def apply(result):
            app.document.apply(lambda _:result,name)
            app.canvas_view.render()
            app.refresh_history()
            app.status(name+' complete.')
        self.submit(lambda:transform(snapshot),name,apply)

    def submit(self,work,name,on_result,on_cancel=None,show_progress=True):
        app = self.app
        if app.busy:
            return False
        revision = app.document.revision
        self.cancel_event = Event()
        app.busy = True
        self.dialog = None
        if show_progress:
            self.dialog = tk.Toplevel(app.root)
            self.dialog.title(name)
            self.dialog.transient(app.root)
            tk.Label(self.dialog,text=name+' — working…',fg=T.TEXT,padx=T.PAD,pady=T.PAD).pack()
            self.progress = ttk.Progressbar(self.dialog,mode='indeterminate')
            self.progress.pack(fill='x',padx=T.PAD,pady=T.GAP)
            self.progress.start()
            RoundedButton(self.dialog,text='Cancel',command=self.cancel).pack(padx=T.PAD,pady=T.GAP)
            self.dialog.protocol('WM_DELETE_WINDOW',self.cancel)
        def run():
            try:
                self.queue.put((work(),None))
            except Exception as exc:
                self.queue.put((None,str(exc)))
        Thread(target=run,daemon=True,name='image-operation').start()
        app.root.after(T.POLL_MS,lambda:self.poll(revision,name,on_result,on_cancel))
        return True

    def cancel(self):
        self.cancel_event.set()
        if self.dialog:
            self.dialog.withdraw()
        self.app.status('Cancelled; waiting for the image library to finish its current operation.')

    def poll(self,revision,name,on_result,on_cancel):
        try:
            result,error = self.queue.get_nowait()
        except Empty:
            self.app.root.after(T.POLL_MS,lambda:self.poll(revision,name,on_result,on_cancel))
            return
        if self.dialog:
            self.progress.stop()
            self.dialog.destroy()
        app = self.app
        app.busy = False
        cancelled = self.cancel_event.is_set() or app.document.revision != revision
        if cancelled or error:
            if on_cancel:
                on_cancel()
            if error and not cancelled:
                messagebox.showerror('Image operation failed',error,parent=app.root)
            else:
                app.status('Operation cancelled; image unchanged.')
        else:
            on_result(result)
