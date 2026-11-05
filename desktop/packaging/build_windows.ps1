# AEGIS Windows 64-bit build. Run from Windows PowerShell, or double-click build-installer.cmd.
# Developer prerequisites: Python 3.11+ (64-bit), Inno Setup 6.3+. End users need neither.
param([switch]$SkipInstaller, [switch]$RunGuiTests)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Check-Exit([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE)." }
}
function Find-InnoCompiler {
    $paths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    foreach ($path in $paths) { if ($path -and (Test-Path $path)) { return $path } }
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}

if ($env:OS -ne 'Windows_NT') { throw 'Use this builder on a 64-bit Windows PC.' }
if (-not (Test-Path 'assets\aegis.ico')) { throw 'Missing assets\aegis.ico.' }
if (-not (Test-Path 'run.py')) { throw 'Missing run.py. Extract the entire ZIP before building.' }
if (-not (Test-Path 'requirements.txt')) { throw 'Missing requirements.txt.' }

# Check for Inno Setup up front, before downloading dependencies.
$compiler = $null
if (-not $SkipInstaller) {
    $compiler = Find-InnoCompiler
    if (-not $compiler) {
        throw 'Install Inno Setup 6.3+ from https://jrsoftware.org/isinfo.php, then rerun. For just the standalone app, use -SkipInstaller.'
    }
    Write-Host "Found Inno Setup: $compiler"
}

$venvPython = Join-Path $root '.venv-build\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    # Use the known working Python command from the developer machine.
    $systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $systemPython) { throw 'Python 3.11+ 64-bit is required on the build PC.' }
    & $systemPython.Source -c "import sys,struct; assert sys.version_info >= (3,11), 'Python 3.11+ required'; assert struct.calcsize('P') == 8, '64-bit Python required'"
    Check-Exit 'Python version / architecture check'
    & $systemPython.Source -m venv '.venv-build'
    Check-Exit 'Creating the build environment'
}

Write-Host 'Installing build dependencies (may take a few minutes on first run)...'
& $venvPython -m pip install --timeout 120 --retries 10 --prefer-binary -r requirements.txt 'pyinstaller>=6.10,<7'
Check-Exit 'Installing Python packages'

# Security and packaging tests are mandatory. These classes do not start
# QApplication and therefore avoid a native Qt shutdown crash seen after an
# otherwise successful all-in-one unittest run on some Windows installations.
Write-Host 'Running mandatory backend and packaging tests...'
& $venvPython 'packaging\run_build_tests.py'
Check-Exit 'Backend and packaging tests'

# Optional diagnostic only. Never suppress the native Windows exit code:
# -1073740791 == 0xC0000409 (fast-fail). GUI acceptance tests remain part of
# the project, and the packaged application must be manually smoke-tested.
if ($RunGuiTests) {
    Write-Host 'Running additional Qt GUI tests (optional)...'
    $previousQtPlatform = $env:QT_QPA_PLATFORM
    try {
        $env:QT_QPA_PLATFORM = 'windows'
        & $venvPython -X faulthandler -m unittest discover -s tests -v
        Check-Exit 'Optional Qt GUI tests'
    }
    finally {
        $env:QT_QPA_PLATFORM = $previousQtPlatform
    }
}
else {
    Write-Host 'Qt GUI tests were not executed by the build gate.' -ForegroundColor Yellow
    Write-Host 'Test the built app with a dummy vault before distribution.' -ForegroundColor Yellow
    Write-Host 'For separate diagnostic GUI tests, rerun with -RunGuiTests.'
}

Write-Host 'Packaging the app and its Python runtime...'
& $venvPython -m PyInstaller --noconfirm --clean --windowed --onedir `
    --name AEGIS --icon 'assets\aegis.ico' --add-data 'assets;assets' `
    --version-file 'packaging\version_info.txt' run.py
Check-Exit 'PyInstaller packaging'
$exePath = Join-Path $root 'dist\AEGIS\AEGIS.exe'
if (-not (Test-Path $exePath)) { throw 'Build completed without dist\AEGIS\AEGIS.exe.' }
Write-Host "Standalone app ready: $exePath"

if ($SkipInstaller) {
    Write-Host 'Only the standalone application folder was built (-SkipInstaller).'
    exit 0
}

Write-Host 'Creating the Windows setup wizard...'
& $compiler (Join-Path $root 'packaging\aegis.iss')
Check-Exit 'Inno Setup installer compilation'
$installer = Join-Path $root 'installer-output\AEGIS-Setup-0.3.9-Windows-x64.exe'
if (-not (Test-Path $installer)) { throw "Installer not found: $installer" }
$hash = (Get-FileHash -Path $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$shaPath = "$installer.sha256"
Set-Content -Encoding Ascii -Path $shaPath -Value "$hash *$(Split-Path $installer -Leaf)"
Write-Host ''
Write-Host 'WINDOWS INSTALLER READY' -ForegroundColor Green
Write-Host "Installer: $installer"
Write-Host "SHA-256:   $hash"
Write-Host 'Next: install and test on Windows using a separate AEGIS_DATA_DIR dummy vault.'
