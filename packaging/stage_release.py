"""Stage reproducible source and notices alongside the frozen application."""
from pathlib import Path
import importlib.metadata
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT/'work/packaging/dist/PyPhotoEditor'


def main():
    BUNDLE.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'LICENSE',BUNDLE/'LICENSE.txt')
    shutil.copy2(ROOT/'packaging/README-WINDOWS.txt',BUNDLE/'README-WINDOWS.txt')
    shutil.copy2(ROOT/'packaging/build-lock.txt',BUNDLE/'dependency-versions.txt')
    with zipfile.ZipFile(BUNDLE/'SourceCode.zip','w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT/'LICENSE','LICENSE')
        for folder in ('pyphotoeditor','tests','packaging'):
            for path in (ROOT/folder).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.exe','.zip','.pyc'):
                    archive.write(path,path.relative_to(ROOT))
        for pattern in ('*.py','*.bat','*.md','*.txt','pytest.ini','.gitignore'):
            for path in ROOT.glob(pattern):
                archive.write(path,path.name)
    licenses = BUNDLE/'ThirdPartyLicenses'
    excluded = {'pytest','iniconfig','pluggy','colorama','pygments','pyinstaller','pyinstaller-hooks-contrib','pefile','pywin32-ctypes','altgraph','setuptools','pip'}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get('Name','unknown')
        if name.lower() in excluded:
            continue
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ('license','copying','notice')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = licenses/name/str(file).replace('..','_')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)


if __name__ == '__main__':
    main()
