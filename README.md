# PyEditor

PyEditor is a desktop, Photoshop-style image editor written in Python, with
a modular architecture built for **low coupling** and **high (functional)
cohesion**.

## Library responsibilities

| Library | Responsibility |
|---|---|
| **Tkinter** | Window, menus, toolbar, canvas, property panel, dialogs, mouse/keyboard events |
| **Pillow** | Image I/O, drawing (brush/shapes), resizing, rotation, compositing |
| **NumPy** | Pixel arrays, Floyd–Steinberg error-diffusion math |
| **SciPy** | Gaussian/median filtering, morphology, connected-component labeling |
| **scikit-image** | Grayscale, Sobel/Canny, CLAHE, TV denoising, Otsu threshold, morphology |
| **scikit-learn** | K-Means color clustering (posterize) |

## File structure

```
pyeditor/
├── requirements.txt
├── run_pyeditor.py            # thin convenience launcher
├── run_pyeditor.bat           # Windows double-click launcher
├── README.md
└── pyeditor/                  # the actual package
    ├── __init__.py
    ├── main.py                 # entry point: builds Tk root, sets icon, starts App
    ├── assets/
    │   ├── logo.svg             # custom vector logo (source of truth)
    │   └── logo.png             # rendered PNG used as the window icon
    ├── core/                   # ---- pure image-processing layer ----
    │   ├── __init__.py           # public API re-exports
    │   ├── document.py           # Document: image state + undo/redo history
    │   ├── image_ops.py          # Pillow basics: grayscale, rotate, flip, resize...
    │   ├── filters.py            # SciPy/scikit-image: blur, sobel, canny, CLAHE, denoise
    │   ├── dithering.py          # NumPy Floyd–Steinberg dithering
    │   └── segmentation.py       # scikit-learn/scikit-image: K-Means, rotoscope
    └── ui/                     # ---- Tkinter presentation layer ----
        ├── __init__.py
        ├── app.py                 # composition root: owns Document, wires UI + core
        ├── menu_bar.py             # top menu -> calls App methods
        ├── toolbar.py              # Open/Save/Undo/Redo/Fit strip
        ├── tool_strip.py           # left tool-selector buttons
        ├── tool_panel.py           # right "PROPERTIES" panel (brush + quick filters)
        ├── canvas_view.py          # zoom/pan/render + routes mouse events to tools
        ├── tools.py                # Brush/Pencil/Eraser/Rect/Ellipse/Crop/Eyedropper
        └── dialogs.py              # New Image / Resize modal dialogs
```

## Why this structure (coupling & cohesion)

- **`core` has zero Tkinter imports.** Every function in `image_ops.py`,
  `filters.py`, `dithering.py`, `segmentation.py` has the exact same shape:
  `Image -> Image` (or `Image -> Image` with plain-value parameters). That
  uniform contract is what lets `Document.apply()` call *any* of them
  interchangeably, and is why `core` can be unit-tested or reused in a
  script/CLI/notebook with no GUI at all.
- **Each `core` module has one job (functional cohesion).** `image_ops.py`
  is Pillow-native transforms; `filters.py` is neighborhood/frequency
  filters; `dithering.py` is halftoning; `segmentation.py` is
  region/clustering logic. Nothing in one module depends on internals of
  another.
- **`ui` modules only depend on `App`, never on each other.** `menu_bar.py`
  and `toolbar.py` just call `app.grayscale()`, `app.undo()`, etc. — they
  don't know `canvas_view.py` or `tools.py` exist. That means you can
  replace the whole toolbar or add a new dialog without touching the
  canvas or the drawing tools.
- **Tools are polymorphic, not `if/elif` chains.** `tools.py` defines one
  small class per tool, all sharing the `on_down/on_move/on_up`
  interface, registered in `TOOL_CLASSES`. `canvas_view.py` forwards
  events to whichever tool is active without any per-tool branching, and
  `tool_strip.py` builds its buttons straight from that same registry —
  adding a new tool touches exactly one file.
- **Undo/redo lives in one place.** `Document` in `document.py` is the only
  thing that mutates history; UI code never pushes/pops the stacks
  directly, it just calls `document.apply(transform)` or `document.undo()`.

## Installation

Python 3.10+ is recommended.

```bash
python -m pip install -r requirements.txt
python run_pyeditor.py
```

On Windows you can also just double-click `run_pyeditor.bat`, or run:

```bash
py -m pip install -r requirements.txt
py run_pyeditor.py
```

You can also launch it as a package:

```bash
python -m pyeditor.main
```

## Included features

### Document / UI
- New document, Open/Save/Save As (PNG, JPEG, WEBP, TIFF)
- Undo/redo, reset to original
- Zoom / fit to window
- Photoshop-style dark UI

### Tools
Brush, Pencil, Eraser, Rectangle, Ellipse, Crop, Eyedropper — adjustable
brush size and color.

### Image operations
Grayscale, Invert, Auto Contrast, Resize, Rotate, Flip.

### Filters / effects
Gaussian blur, Median filter, Unsharp mask, Sobel edges, Canny edges,
CLAHE, Total-variation denoising, Floyd–Steinberg dithering, K-Means
posterization, experimental automatic rotoscope/foreground extraction.

## Notes

This is a solid modular foundation, not a full replacement for Adobe
Photoshop. The natural next step for a production-grade editor would be a
real layer system, non-destructive adjustment stack, selection masks,
text/vector tools, GPU acceleration, and a project file format — all of
which would slot into this same `core`/`ui` split without restructuring
what already exists.
