"""
ui
==
Tkinter presentation layer. Each module owns exactly one piece of screen:

    app.py          the App shell: window, wires everything together
    menu_bar.py       top menu (File/Edit/Image/Filters/Help)
    toolbar.py         quick-action button strip
    tool_panel.py       right-hand properties panel (brush size/color, quick filters)
    canvas_view.py       the drawing surface: zoom, pan, render, mouse routing
    tools.py             pointer tool behaviors (brush, eraser, shapes, crop, eyedropper)
    dialogs.py           small modal dialogs (New Image, Resize)

Every module here talks to the shared `core.Document` instance owned by
`App` -- never to each other's internals directly -- which keeps coupling
low: e.g. `toolbar.py` can be swapped out without touching `canvas_view.py`.
"""
