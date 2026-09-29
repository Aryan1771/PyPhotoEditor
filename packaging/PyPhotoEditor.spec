# Run from the repository root with: python -m PyInstaller packaging/PyPhotoEditor.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

project = Path(SPECPATH).parent
without_tests = lambda name: '.tests' not in name and '.testing' not in name
hidden = collect_submodules('skimage', filter=without_tests)
hidden += collect_submodules('sklearn', filter=without_tests)
data = collect_data_files('skimage', includes=['**/*.pyi'])
data += [(str(project / 'LICENSE'), '.'), (str(project / 'README.md'), '.')]
a = Analysis(
    [str(project / 'run_pyphotoeditor.py')],
    pathex=[str(project)], binaries=[], datas=data,
    hiddenimports=hidden,
    excludes=['pytest', 'IPython', 'matplotlib', 'pandas', 'torch', 'tensorflow',
              'tkinter.test', 'numpy.tests', 'scipy.tests'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PyPhotoEditor',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(project / 'work' / 'packaging' / 'app.ico'),
          version=str(project / 'packaging' / 'version.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PyPhotoEditor')
