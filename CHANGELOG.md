# Changelog

## 2026-09-28 — PyPhotoEditor brush-effects upgrade

- Renamed package, launchers, window, About and artwork from PyEditor to PyPhotoEditor.
- Added centralized dark theme, generated icons, Canvas controls, grouped sidebar, contextual options, collapsible Properties/History panel and themed menu popups.
- Added checkerboard transparency, viewport clipping, dirty patch display updates, brush outlines, cursor-centered zoom and Space/middle panning.
- Added cached circle/square masks, soft hardness, strength, stroke-start coverage memory, build-up mode and optional selection masks.
- Replaced full-image stroke undo with exact patch commands and a 512 MiB command-history budget; retained snapshot commands for whole-image operations.
- Added all requested Magic brushes; migrated Brush/Pencil/Eraser to the shared engine and kept shapes/crop/eyedropper and existing menus.
- Added Lab background removal with contiguous regions, sampling modes, soft alpha, defringe and original-image restoration.
- Preserved alpha in existing RGB filters; added white-matte JPEG export with a warning.
- Moved global effects and stroke preparation to workers; added cancellation, stale-result protection, bounded stroke batches and queued rapid strokes.
- Added headless correctness tests, real Tk integration tests and 12 MP performance smoke tests. Removed tracked bytecode and added ignore rules.

Runtime libraries remain Tkinter, Pillow, NumPy, SciPy, scikit-image and scikit-learn. Additional Python libraries are permitted; none was necessary for this implementation.
