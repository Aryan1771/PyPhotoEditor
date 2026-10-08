# PyPhotoEditor

A dark desktop image editor with Tux Paint-style **Magic effect brushes**. Paint an effect directly onto a photograph, including transparent images. Python 3.10+; tested on Windows with Python 3.13.

## Install and launch

```powershell
python -m pip install -r requirements.txt
python run_pyphotoeditor.py
```

Windows users can double-click `run_pyphotoeditor.bat`. The equivalent package entry point is `python -m pyphotoeditor.main`.

## Editing

- Open a photo or create a document. Select a drawing or Magic tool from the scrollable left sidebar.
- The top options bar controls circle/square shape, size (1–500 image pixels), strength and circle hardness. Numeric fields accept values with Enter or focus loss. `[` and `]` change size.
- **Once per stroke** is the default: overlapping passes within one drag do not apply the effect twice. Release and start another stroke to apply it again. **Build up** repeatedly applies stamps to the current result. Smudge is stateful and carries color between stamps in either mode.
- Brush, Pencil and Eraser share this engine. Rectangle, Ellipse and Crop retain drag-box behavior; Eyedropper samples a pixel. Choose paint color in Properties.
- **Lasso** creates a freehand selection. **Magic Wand** selects a connected region of similar colors with adjustable Lab-color tolerance. The selection clips paint, Magic brushes, gradients, and symbol stamps; clear it from the tool settings drawer.
- **Select Subject** and **Background Removal** use local OpenCV GrabCut with no model download or network access. Drag a box around the subject; the tool creates a soft foreground selection or removes the background. This is classical image segmentation, so complex hair, transparent objects, and low-contrast subjects may need manual cleanup.
- **Gradient** fills a drag-box with horizontal, vertical, diagonal, or radial two-color gradients, clipped to the active selection. **Symbol / Stamp** opens the Symbol Studio for cell-by-cell pixel art, freehand artwork, or a local image stamp; click the canvas to place the created symbol.
- Magic brushes: Blur, Sharpen, Smudge, Pixelate, Grayscale, Negative, Sepia, Emboss, Edge Glow, Posterize, Ordered Dither, Oil Paint, Noise/Grain, Hue Shift, Dodge/Burn, Sponge and Cartoon.
- Wheel zooms toward the pointer. Middle-drag or Space+left-drag pans. Fit resets the viewport. Transparency is displayed over a checkerboard.
- Properties toggles the right panel. History contains named actions; click any retained state to jump to it. Ctrl+Z / Ctrl+Y undo and redo. Ctrl+N / Ctrl+O / Ctrl+S create, open and save.

All original Image and Filters menu operations remain: grayscale, invert, auto contrast, resize, rotate, flips, Gaussian/median/unsharp, Sobel/Canny, CLAHE, TV denoising, Floyd–Steinberg dithering, K-Means posterization and experimental rotoscope extraction. Global processing runs in a worker with an indeterminate progress indicator and Cancel. RGB effects preserve alpha; Eraser, Background Eraser, Restore, paint and rotoscope intentionally modify it.

## Background removal

Choose **Background Eraser**, then paint over the background. Defaults: fixed white target, Lab tolerance 25, softness 10, contiguous limits, defringe off.

- Tolerance is Euclidean CIE Lab distance, controlled from 0 to 100. Softness blends the alpha transition over `[max(0, tolerance-softness), tolerance]`. Softness zero gives a hard threshold.
- Fixed white always targets white. Sample at stroke start targets the first pixel. Continuous samples the stroke-start image under each stamp.
- Contiguous mode uses four-neighbor connected components seeded by matching pixels under the first footprint. It preserves enclosed white regions that the first footprint did not touch. For continuous sampling, this initial connectivity mask stays fixed throughout the stroke. Discontiguous mode removes all matching painted pixels.
- Connectivity analysis runs in a worker. Pointer samples received during preparation are queued and painted afterward. Cancel discards the stroke.
- Defringe removes the sampled matte from partially transparent edge pixels. The eraser only lowers alpha and uses the same stroke memory as other effects.
- Restore paints original pixels and alpha back. It is disabled when current canvas dimensions differ from the loaded/new original; undoing the size change re-enables it. Original coordinates are used even after a same-size transform.

PNG, WEBP and TIFF preserve alpha. JPEG export warns and composites onto white. There is no layer/project file format.

## Architecture

```text
PyPhotoEditor/
├── run_pyphotoeditor.py / run_pyphotoeditor.bat
├── requirements.txt / requirements-dev.txt
├── tests/                       # headless core, Tk integration, performance
└── pyphotoeditor/
    ├── main.py                  # desktop entry point
    ├── assets/                  # branded reference artwork
    ├── core/                    # zero tkinter imports
    │   ├── document.py          # Document, SnapshotCommand, PatchCommand
    │   ├── brush.py             # immutable brush + cached float32 footprints
    │   ├── stroke.py            # stroke-start pixels, coverage, dirty patches
    │   ├── brush_effects.py     # effect registry and parameter schemas
    │   ├── bg_eraser.py         # Lab distance, connected masks, defringe, restore
    │   ├── drawing.py / export.py / alpha.py
    │   └── image_ops.py / filters.py / dithering.py / segmentation.py
    └── ui/
        ├── app.py               # composition and command coordination
        ├── theme.py             # colors, fonts, dimensions, ttk/platform style
        ├── widgets.py / icons.py # Canvas controls and generated PIL artwork
        ├── canvas_view.py       # viewport, checkerboard, dirty rendering, input
        ├── tools.py             # pointer adapters; no pixel algorithms
        ├── tool_options.py      # schema-driven options
        ├── worker.py            # queue-based main-thread result delivery
        └── menu_bar.py / toolbar.py / tool_strip.py / tool_panel.py / dialogs.py
```

**Library choices:** scikit-image handles color spaces and edge processing, SciPy handles neighborhood filters and connected components, and NumPy vectorizes masks/blending/dithering. Pillow handles image I/O, drawing and display conversion. scikit-learn retains K-Means. OpenCV provides the GrabCut-based selection and background-removal tools.

### Stroke and history contracts

`StrokeSession(document, effect, brush, mode, params)` snapshots RGBA pixels and allocates work/coverage arrays. Stamps interpolate at 15% of brush diameter. Once-per-stroke coverage is the maximum masked strength reached at each pixel; results always derive from the stroke-start source, with explicit padding for neighborhood filters. Mosaic blocks, Bayer thresholds and noise are anchored to image coordinates. Selection is an optional float32 `Document.selection` array of shape H×W, values 0–1.

The UI prepares buffers in a worker, then processes interpolated stamps in short main-thread batches. Only dirty display patches are uploaded during painting. Rapid successive strokes are queued. Document commands wait for active strokes to finish. Workers communicate through a queue; only callbacks polled by `root.after` access Tk. Obsolete worker results are rejected using the document revision.

Each changed stroke records one `PatchCommand(bbox, before, after, name)`. Whole-image operations record `SnapshotCommand`. `Document.apply(transform, name=None)` remains compatible with existing Image→Image functions. Undo/redo restore bytes exactly. The default history budget is **512 MiB**, configurable as `Document(memory_budget=...)`; oldest commands are evicted. A single command larger than the budget is not retained. The budget covers retained commands, not the original image, current image or active stroke buffers. The first History row is the earliest retained state after eviction.

### Add a brush effect

Add this entry to `core/brush_effects.py`; the sidebar and parameter controls discover it automatically on startup:

```python
def warm(roi, params):
    out = roi.copy()
    out[..., 0] = np.clip(roi[..., 0].astype(float) + params['amount'], 0, 255)
    return out
EFFECTS['warm'] = Effect('Warm', warm, params={'amount': number(20, 0, 100)})
```

Effects accept RGBA uint8 arrays and return the same shape/dtype. Declare `pad` (integer or parameter-dependent function) for neighborhood filters. Alpha is preserved automatically unless `alpha_effect=True`. `stateful=True` opts into carried-state/build-up behavior; `_state` is private to one stroke. `_origin` contains the ROI's image-space coordinates. Do not mutate an input array or document.

## Validation

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pytest -q -s -m slow
python -m compileall -q pyphotoeditor
```

Core tests require no display. Tk tests run when a display can be initialized, otherwise report a skip. Performance tests use 4000×3000 images and 200-pixel circles; they measure median core stamp + patch publication time, excluding one-time buffer allocation, plus UI pointer-handler latency. Timing is machine-dependent. Measured core medians on the development machine were approximately 3–5 ms for Negative, Blur and Pixelate, below the 30 ms target.

### Manual UI checklist

- [ ] Launch using Python and the Windows launcher. Check title, About, icon and dark menus.
- [ ] At 1000×700 and a larger window, select every tool; verify options fit and the sidebar scrolls. Toggle Properties.
- [ ] Open an RGBA PNG; verify checkerboard, zoom toward the cursor, Space/middle panning and Fit.
- [ ] Paint a self-crossing Negative stroke with a soft circle and a square. Check one history entry, exact Undo/Redo, and History jumps across a resize.
- [ ] Try `[`, `]`, numeric size, strength and hardness, then Build up. Try quick successive strokes, Smudge and all Magic effects.
- [ ] Remove a white background in contiguous mode; verify an enclosed white island survives. Compare discontiguous, both sampling modes, tolerance, softness and defringe.
- [ ] Restore erased pixels. Resize/crop and confirm Restore is disabled; undo and confirm it returns.
- [ ] Save/reopen PNG, WEBP and TIFF with transparency. Save JPEG, check the warning and white background.
- [ ] Run and cancel K-Means/CLAHE/denoise. Open a different document while processing; confirm the stale result never replaces it.
- [ ] Draw rectangle/ellipse, crop, use Eyedropper, and exercise the retained image/filter menu items.

### Practical limits

Cancel is cooperative at the operation boundary: native/library work already running completes in its worker, but its result is discarded. Another worker operation waits until that work returns. Progress is indeterminate because those library APIs do not expose incremental progress. Large/high-radius brushes can take longer per stamp; long drags are split into batches, but an individual stamp cannot be interrupted. Stroke buffer preparation and connected-background analysis can add initial latency while the UI stays responsive. Smudge is a simple carried-color brush, not a fluid simulation. The optional Ctrl+K command palette is not included.


## Standalone Windows app and installer (local build)

`packaging/build.ps1` produces a windowed PyInstaller application and a single-file Inno Setup installer in `installers/`. The installer targets Windows 10/11 x64-compatible systems, bundles Python and codecs, installs per-user, and includes Start menu shortcuts, optional desktop/Explorer integration, and an uninstaller. It does not change default image associations. On Windows 11 the static context-menu command is normally under **Show more options**. Install Inno Setup and pass `-InnoCompiler` if `ISCC.exe` is not in the local build-tool folder. Runtime and build requirements are in `requirements-app.txt` and `requirements-build.txt`; `packaging/build-lock.txt` records the tested versions.

New import support includes HEIC/HEIF, AVIF, SVG and LibRaw camera formats. SVG is rasterized; animations/multipage documents edit the first frame/page, and PSD uses its merged image. Import-only formats route to Save As PNG to preserve the original. EXIF orientation is honored. Saves are atomic; unsuccessful writes preserve the existing file and filename. Unsaved changes prompt before document replacement or closing. Invalid or excessively large dimensions produce a normal dialog instead of a callback error.

The explicit `PyPhotoEditor.exe --self-test DIRECTORY` diagnostic runs format, filter, and Tk editing checks and writes `DIRECTORY/report.json`. It does not run during normal use. The installed distribution includes `SourceCode.zip`, dependency versions and available third-party licenses.

## Ubuntu / Debian

On Ubuntu 24.04+ or Debian 13+ x86-64, run `bash packaging/build-debian.sh`. The script builds and tests a self-contained PyInstaller application, then emits `PyPhotoEditor-1.1.0-Ubuntu-amd64.deb` and its SHA-256 checksum in `installers/`. Install with `sudo apt install ./PyPhotoEditor-1.1.0-Ubuntu-amd64.deb`, or open the `.deb` in the system software installer. The package provides a desktop entry and `pyphotoeditor` command. Editing works offline after installation. Debian and Ubuntu releases can differ in system library compatibility, so build the `.deb` on the oldest distribution you intend to support.
### Linux Installation (Ubuntu/Debian)

The official Linux installer is hosted right here in the repository. Because the binary is tracked via **Git LFS (Large File Storage)**, please use one of the two methods below to ensure you download the complete, working package rather than a text pointer.

### Download the packaged installer
1. Go directly to the [PyPhotoEditor Installers Directory](https://github.com/Aryan1771/PyPhotoEditor/tree/main/installers).
2. Click on the `PyPhotoEditor-1.1.0-Ubuntu-amd64.deb` file.
3. Click the **Download raw file** button (or the **Download** button in the upper right) to save the full binary to your system.

### Clone with Git LFS
If you are cloning this entire repository via your terminal, you must have the `git-lfs` extension installed to fetch the actual installer binary:

```bash
# 1. Install Git LFS (if you haven't already)
sudo apt install git-lfs

# 2. Set up Git LFS in your local environment
git lfs install

# 3. Clone the repository and pull the actual LFS files
git clone https://github.com/Aryan1771/PyPhotoEditor.git
cd PyPhotoEditor
git lfs pull
```

### Installing the `.deb` Package
Once you have downloaded the actual `PyPhotoEditor-1.1.0-Ubuntu-amd64.deb` file, open your terminal in the directory where the file is located and run:

```bash
sudo apt update
sudo apt install ./PyPhotoEditor-1.1.0-Ubuntu-amd64.deb
```

*(Optional)* To verify that your file downloaded completely without corruption, you can cross-reference it against the provided `SHA256SUMS-Linux.txt` checksum file:
```bash
sha256sum -c SHA256SUMS-Linux.txt
```

The repository includes a Linux installer tracked through Git LFS. Use the source build scripts to reproduce packages for Windows or Debian/Ubuntu.

## License

See [LICENSE](LICENSE) for the GNU GPL v3 terms.
