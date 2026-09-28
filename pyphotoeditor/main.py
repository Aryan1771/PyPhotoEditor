"""Desktop entry point; all platform and presentation policy lives in ui."""
import tkinter as tk
from PIL import ImageTk
from .ui.app import App
from .ui.icons import app_icon


def main():
    root = tk.Tk()
    App(root)
    root._icon_ref = ImageTk.PhotoImage(app_icon(),master=root)
    root.iconphoto(True,root._icon_ref)
    root.mainloop()


if __name__ == '__main__':
    main()
