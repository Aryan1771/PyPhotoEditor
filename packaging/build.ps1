param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\work\packaging\installer'),
    [string]$InnoCompiler = (Join-Path $PSScriptRoot '..\work\tools\InnoSetup\ISCC.exe')
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $projectRoot
try {
    $buildPython = Join-Path $projectRoot 'work\app-env\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $buildPython)) {
        python -m venv work/app-env
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    & $buildPython -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $buildPython -m pip freeze > packaging/build-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $buildPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; no installer built.' }
    & $buildPython -c "from pathlib import Path; from pyphotoeditor.ui.icons import app_icon; Path('work/packaging').mkdir(parents=True,exist_ok=True); app_icon().save('work/packaging/app.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
    & $buildPython -m PyInstaller --noconfirm --distpath work/packaging/dist --workpath work/packaging/build packaging/PyPhotoEditor.spec
    if ($LASTEXITCODE -ne 0) { throw 'Application freezing failed.' }
    $builtExe = Join-Path $projectRoot 'work\packaging\dist\PyPhotoEditor\PyPhotoEditor.exe'
    & $builtExe --self-test (Join-Path $projectRoot 'work\packaging\build-smoke')
    if ($LASTEXITCODE -ne 0) { throw 'Frozen application smoke test failed.' }
    & $buildPython -c "import runpy; runpy.run_path('packaging/generate_context_menu.py',run_name='__main__')"
    & $buildPython packaging/stage_release.py
    $frozenExe = Join-Path $projectRoot 'work\packaging\dist\PyPhotoEditor\PyPhotoEditor.exe'
    $smokeDirectory = Join-Path $projectRoot 'work\packaging\build-smoke'
    $smokeProcess = Start-Process -FilePath $frozenExe -ArgumentList '--self-test',('"' + $smokeDirectory + '"') -WindowStyle Hidden -Wait -PassThru
    if ($smokeProcess.ExitCode -ne 0) { throw 'Frozen application smoke test failed.' }
    if (-not (Test-Path -LiteralPath $InnoCompiler)) { throw 'Install Inno Setup and pass its ISCC.exe path with -InnoCompiler.' }
    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $releaseOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path
    & $InnoCompiler ('/O' + $releaseOutput) packaging/PyPhotoEditor.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
    $installer = Get-ChildItem -LiteralPath $releaseOutput -Filter '*Setup.exe' | Select-Object -First 1
    $hash = Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256
    "$($hash.Hash)  $($installer.Name)" | Set-Content -Encoding ascii (Join-Path $releaseOutput 'SHA256SUMS.txt')
}
finally { Pop-Location }
