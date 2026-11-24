param(
    [string]$Python = (Join-Path $PSScriptRoot '..\work\bake-env\Scripts\python.exe'),
    [string]$Output = (Join-Path $PSScriptRoot '..\PSVita_READY')
)

$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$name = 'Mortal Kombat 9 Remaster 206 Installer'
$payload = Join-Path $PSScriptRoot 'payload'
$helpImages = Join-Path $PSScriptRoot 'help-images'
$tools = Join-Path $PSScriptRoot 'tools\xdelta3-3.2.2-windows-x86_64'
$toolDestination = 'tools/xdelta3-3.2.2-windows-x86_64'
$build = Join-Path $env:TEMP 'mk9-206-package'
if (!(Test-Path (Join-Path $payload 'catalog.json'))) {
    throw 'Run build_payload.py with the clean sources before packaging.'
}

& (Join-Path $PSScriptRoot 'prepare_help_images.ps1')

$arguments = @(
    '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', '--noupx',
    '--exclude-module', 'numpy',
    '--name', $name, '--distpath', $Output, '--workpath', (Join-Path $build 'work'), '--specpath', $build,
    '--paths', (Join-Path $project 'work'),
    '--paths', (Join-Path $project 'work\es4-clock'),
    '--paths', (Join-Path $project 'work\native-960'),
    '--add-data', "${payload}:payload",
    '--add-data', "$(Join-Path $helpImages 'vita3k-en-inline.png'):help-images",
    '--add-data', "$(Join-Path $helpImages 'vita3k-ru-inline.png'):help-images",
    '--add-data', "$(Join-Path $helpImages 'vita-shell.gif'):help-images",
    '--add-data', "$(Join-Path $helpImages 'fagdec.gif'):help-images",
    '--add-binary', "$(Join-Path $tools 'xdelta3.exe'):${toolDestination}",
    '--add-data', "$(Join-Path $tools 'LICENSE'):${toolDestination}",
    (Join-Path $PSScriptRoot 'installer.py')
)
& $Python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller returned exit code $LASTEXITCODE."
}
