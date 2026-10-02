#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${PYPHOTOEDITOR_BUILD_DIR:-/tmp/pyphotoeditor-linux-build}"
VENV="$BUILD_ROOT/venv"
VERSION="${PYPHOTOEDITOR_VERSION:-1.1.0}"
ARCH="$(dpkg --print-architecture)"
DIST="$BUILD_ROOT/dist"
PACKAGE="$BUILD_ROOT/package-root"
OUT="${1:-$ROOT/installers}"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "Install dpkg-dev before building (Ubuntu/Debian: sudo apt install dpkg-dev)." >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then
  echo "Install Python and venv support (Ubuntu/Debian: sudo apt install python3 python3-venv python3-tk)." >&2
  exit 2
fi

mkdir -p "$BUILD_ROOT" "$OUT"
# Build Tk-enabled Linux bundles without requiring root on the builder host.
# These packages are extracted to a private build directory and never installed
# on the build machine; PyInstaller bundles the interpreter's Tk dependencies.
TK_ROOT="$BUILD_ROOT/tk-deps"
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
  mkdir -p "$TK_ROOT/downloads" "$TK_ROOT/root"
  if [[ -z "$(find "$TK_ROOT/root/usr/lib" -path '*/lib-dynload/_tkinter*.so' -print -quit 2>/dev/null || true)" ]]; then
    if [[ "$PY_VER" == "3.12" ]] && grep -q 'VERSION_ID="24.04"' /etc/os-release; then
      (cd "$TK_ROOT/downloads" && apt download python3-tk libtcl8.6 libtk8.6 tcl8.6 tk8.6 blt tk8.6-blt2.5 libxss1 python3.12-venv=3.12.3-1 python3-pip-whl python3-setuptools-whl)
    else
      (cd "$TK_ROOT/downloads" && apt download python3-tk libtcl8.6 libtk8.6 tcl8.6 tk8.6 blt tk8.6-blt2.5 libxss1 "python${PY_VER}-venv" python3-pip-whl python3-setuptools-whl)
    fi
    for archive in "$TK_ROOT"/downloads/*.deb; do dpkg-deb -x "$archive" "$TK_ROOT/root"; done
  fi
  export PYTHONPATH="$TK_ROOT/root/usr/lib/python$PY_VER:$TK_ROOT/root/usr/lib/python$PY_VER/lib-dynload${PYTHONPATH:+:$PYTHONPATH}"
  export LD_LIBRARY_PATH="$TK_ROOT/root/usr/lib/x86_64-linux-gnu:$TK_ROOT/root/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export TCL_LIBRARY="$TK_ROOT/root/usr/share/tcltk/tcl8.6"
  export TK_LIBRARY="$TK_ROOT/root/usr/share/tcltk/tk8.6"
fi
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then echo "Could not initialize Python Tk; install python3-tk and retry." >&2; exit 2; fi
if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  rm -rf "$VENV"
  python3 -m venv --without-pip "$VENV"
  # Ubuntu splits ensurepip wheels from the stdlib. Seed this private venv
  # directly from the wheel extracted above, so this build needs no sudo.
  PIP_WHEEL="$(find "$BUILD_ROOT/tk-deps/root/usr/share/python-wheels" -maxdepth 1 -name 'pip-*.whl' -print -quit 2>/dev/null || true)"
  if [[ -z "$PIP_WHEEL" ]]; then
    WHEEL_DIR="$BUILD_ROOT/bootstrap-wheels"; mkdir -p "$WHEEL_DIR"
    (cd "$WHEEL_DIR" && apt download python3-pip-whl)
    dpkg-deb -x "$WHEEL_DIR"/*.deb "$BUILD_ROOT/tk-deps/root"
    PIP_WHEEL="$(find "$BUILD_ROOT/tk-deps/root/usr/share/python-wheels" -maxdepth 1 -name 'pip-*.whl' -print -quit)"
  fi
  SITE="$($VENV/bin/python -c 'import site; print(site.getsitepackages()[0])')"
  mkdir -p "$SITE"
  PIP_WHEEL="$PIP_WHEEL" SITE="$SITE" "$VENV/bin/python" -c 'import os,zipfile; zipfile.ZipFile(os.environ["PIP_WHEEL"]).extractall(os.environ["SITE"])'
fi
"$VENV/bin/python" -m pip install -r "$ROOT/requirements-build.txt"
"$VENV/bin/python" -m pytest -q "$ROOT"
"$VENV/bin/python" -m PyInstaller --noconfirm --clean \
  --distpath "$DIST" --workpath "$BUILD_ROOT/build" "$ROOT/packaging/PyPhotoEditor.spec"
"$DIST/PyPhotoEditor/PyPhotoEditor" --help >/dev/null

rm -rf "$PACKAGE"
APP_DIR="$PACKAGE/opt/pyphotoeditor"
mkdir -p "$APP_DIR" "$PACKAGE/usr/bin" "$PACKAGE/usr/share/applications" "$PACKAGE/usr/share/icons/hicolor/256x256/apps"
cp -a "$DIST/PyPhotoEditor/." "$APP_DIR/"
if [[ -f "$ROOT/pyphotoeditor/assets/logo.svg" ]]; then cp "$ROOT/pyphotoeditor/assets/logo.svg" "$PACKAGE/usr/share/icons/hicolor/256x256/apps/pyphotoeditor.svg"; fi
cat > "$PACKAGE/usr/bin/pyphotoeditor" <<'LAUNCHER'
#!/bin/sh
exec /opt/pyphotoeditor/PyPhotoEditor "$@"
LAUNCHER
chmod 755 "$PACKAGE/usr/bin/pyphotoeditor"
cat > "$PACKAGE/usr/share/applications/pyphotoeditor.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=PyPhotoEditor
Comment=Offline desktop image editor
Exec=pyphotoeditor %F
Icon=pyphotoeditor
Terminal=false
Categories=Graphics;RasterGraphics;2DGraphics;
MimeType=image/png;image/jpeg;image/webp;image/tiff;image/bmp;image/gif;
DESKTOP
mkdir -p "$PACKAGE/DEBIAN"
cat > "$PACKAGE/DEBIAN/control" <<CONTROL
Package: pyphotoeditor
Version: $VERSION
Section: graphics
Priority: optional
Architecture: $ARCH
Maintainer: PyPhotoEditor Project
Depends: libc6 (>= 2.39)
Description: Offline desktop photo editor
 A Python desktop image editor with drawing, selection, foreground extraction,
 gradients, symbols, filters and support for transparent images.
CONTROL
cat > "$PACKAGE/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database -q || true; fi
exit 0
POSTINST
chmod 755 "$PACKAGE/DEBIAN/postinst"
OUTPUT="$OUT/PyPhotoEditor-${VERSION}-Ubuntu-${ARCH}.deb"
dpkg-deb --root-owner-group --build "$PACKAGE" "$OUTPUT"
dpkg-deb --info "$OUTPUT" >/dev/null
dpkg-deb --contents "$OUTPUT" > "$BUILD_ROOT/package-contents.txt"
grep -q 'usr/bin/pyphotoeditor' "$BUILD_ROOT/package-contents.txt"
sha256sum "$OUTPUT" > "$OUT/SHA256SUMS-Linux.txt"
echo "Created $OUTPUT"
