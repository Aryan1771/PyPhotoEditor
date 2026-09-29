"""Local image decoding, orientation and format capabilities; no UI dependencies."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps

RASTER_EXTENSIONS = (
    '.png', '.apng', '.jpg', '.jpeg', '.jpe', '.jfif', '.webp', '.bmp', '.dib',
    '.tif', '.tiff', '.gif', '.ico', '.cur', '.avif', '.avifs', '.heic', '.heif',
    '.hif', '.j2k', '.jp2', '.jpx', '.jpf', '.pcx', '.tga', '.ppm', '.pgm',
    '.pbm', '.pnm', '.psd', '.dds', '.qoi', '.sgi', '.rgb', '.rgba', '.icns',
    '.xbm', '.xpm', '.mpo',
)
RAW_EXTENSIONS = ('.dng', '.cr2', '.cr3', '.crw', '.nef', '.nrw', '.arw', '.srf',
                  '.sr2', '.orf', '.rw2', '.raf', '.pef', '.raw', '.rwl', '.3fr',
                  '.fff', '.iiq', '.kdc', '.dcr', '.mos', '.mrw', '.x3f')
SUPPORTED_EXTENSIONS = tuple(sorted(set(RASTER_EXTENSIONS + RAW_EXTENSIONS + ('.svg',))))
DIRECT_SAVE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff'}


@dataclass
class LoadedImage:
    image: Image.Image
    source: str
    format: str
    frames: int = 1

    @property
    def save_path(self):
        # Never overwrite animations, layered sources, vectors or camera originals
        # with a flattened frame; route them through Save As PNG instead.
        if self.frames == 1 and Path(self.source).suffix.lower() in DIRECT_SAVE_EXTENSIONS:
            return self.source
        return None


def load_image(path):
    path = Path(path).expanduser().resolve(strict=True)
    suffix = path.suffix.lower()
    if suffix in RAW_EXTENSIONS:
        try:
            import rawpy
        except ImportError as exc:
            raise ValueError('Camera RAW support requires requirements-app.txt.') from exc
        with rawpy.imread(str(path)) as raw:
            image = Image.fromarray(raw.postprocess(use_camera_wb=True, output_bps=8))
        return LoadedImage(image.convert('RGBA'), str(path), 'Camera RAW')
    if suffix == '.svg':
        try:
            import resvg_py
        except ImportError as exc:
            raise ValueError('SVG support requires requirements-app.txt.') from exc
        # Decode a local SVG into a raster editing canvas at its intrinsic size.
        data = resvg_py.svg_to_bytes(svg_path=str(path))
        with Image.open(BytesIO(data)) as image:
            return LoadedImage(image.convert('RGBA'), str(path), 'SVG')
    if suffix in ('.heic', '.heif', '.hif'):
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError as exc:
            raise ValueError('HEIC/HEIF support requires requirements-app.txt.') from exc
    with Image.open(path) as image:
        frames = getattr(image, 'n_frames', 1)
        image.seek(0)
        return LoadedImage(ImageOps.exif_transpose(image).convert('RGBA'), str(path), image.format or suffix, frames)
