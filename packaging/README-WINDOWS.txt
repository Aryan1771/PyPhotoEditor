PYPHOTOEDITOR 1.1.0 — WINDOWS APP

Run PyPhotoEditor.exe, or install with PyPhotoEditor-1.1.0-Windows-x64-Setup.exe.
Python and all image libraries are included. Installation and editing work offline.

Requirements: Windows 10 or Windows 11, 64-bit Intel/AMD. Windows 11 ARM64 can
use its x64 emulation but has not been tested. This is not a macOS/Linux installer.
Install is per-user and does not normally need administrator access.

OPEN AND EDIT
- Open images with File > Open / Ctrl+O, or right-click an image and choose
  Edit in PyPhotoEditor. On Windows 11, look under Show more options.
- The installer offers Explorer integration and an optional desktop shortcut.
  It also adds a Start menu entry and a normal Windows uninstaller.
- Default image associations are preserved.
- PNG, JPEG, WEBP, BMP, TIFF, GIF, ICO, AVIF, HEIC/HEIF, JPEG 2000, QOI,
  SVG and LibRaw-supported camera formats are included. Camera support depends
  on the model/format supported by bundled LibRaw.
- Animations/multipage files edit their first frame/page. SVG is rasterized and
  PSD uses its merged image. This is a raster editor, not a layer/animation editor.
- SVG, RAW, HEIC and other import-only formats use Save As PNG by default.
- Save as PNG/WEBP/TIFF to preserve alpha; JPEG flattens onto white.
- Failed saves leave existing files intact. Unsaved changes prompt before
  closing, creating a new document, or opening another image.
- Cancel in a long-running filter discards its result after the library returns.
- Use Lasso or Magic Wand to select image regions. Select Subject and Background
  Removal use local GrabCut without downloading a model or contacting a service.
- Gradient adds linear or radial fills. Symbol Studio creates pixel art, freehand
  artwork, or stamps from local images. Tool options are in a collapsible drawer
  at the bottom of the editor.

SHARING
Share the single Setup.exe; friends do not need this source repository or Python.
Keep the whole folder together if using the portable version instead. Moving
only PyPhotoEditor.exe away from _internal will prevent it from starting.

This installer is not code-signed. Windows may display an unknown-publisher
warning for an independently distributed build. A SHA-256 checksum accompanies
this release so the downloaded file can be compared to the original.

UNINSTALL
Use Windows Settings > Apps > PyPhotoEditor > Uninstall, or the Start menu
Uninstall PyPhotoEditor entry. App-owned context-menu entries and shortcuts
are removed; saved images are not removed.

SOURCE AND LICENSES
The application is GPL-3.0; see LICENSE.txt. SourceCode.zip contains this build's
application source, tests and packaging scripts. ThirdPartyLicenses contains
the included dependencies' available license/notice files. See dependency-
versions.txt for exact bundled Python package versions.
