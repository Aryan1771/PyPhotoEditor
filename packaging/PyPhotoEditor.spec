# Run from the repository root with: python -m PyInstaller packaging/PyPhotoEditor.spec
from pathlib import Path
project = Path(SPECPATH).parent
icon_path = project / 'work' / 'packaging' / 'app.ico'
data = [(str(project / 'LICENSE'), '.'), (str(project / 'README.md'), '.')]
a = Analysis(
    [str(project / 'run_pyphotoeditor.py')],
    pathex=[str(project)], binaries=[], datas=data,
    # Keep only directly imported image algorithms; PyInstaller's normal hooks
    # collect their runtime dependencies without shipping unused estimators,
    # sample image datasets, test modules, or typing stubs.
    hiddenimports=[],
    excludes=['pytest', 'IPython', 'matplotlib', 'pandas', 'torch', 'tensorflow',
              'tkinter.test', 'numpy.tests', 'scipy.tests'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PyPhotoEditor',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(icon_path) if icon_path.is_file() else None,
          version=str(project / 'packaging' / 'version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PyPhotoEditor')
