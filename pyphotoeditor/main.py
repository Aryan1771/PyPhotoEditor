"""Desktop executable entry point, including Explorer file arguments."""
import argparse
import multiprocessing
import subprocess
import sys
import tkinter as tk
from PIL import ImageTk
from .ui.app import App
from .ui.icons import app_icon

VERSION = '1.1.0'


def main(argv=None):
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(prog='PyPhotoEditor')
    parser.add_argument('images', nargs='*', help='Local images to open')
    parser.add_argument('--self-test', metavar='DIRECTORY', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.self_test:
        from .diagnostics import run_self_test
        return run_self_test(args.self_test)
    root = tk.Tk()
    app = App(root)
    root._icon_ref = ImageTk.PhotoImage(app_icon(), master=root)
    root.iconphoto(True, root._icon_ref)
    if args.images:
        root.after_idle(lambda: app.open_image(args.images[0]))
        for path in args.images[1:]:
            command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'pyphotoeditor.main']
            subprocess.Popen(command + ['--', path])
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
