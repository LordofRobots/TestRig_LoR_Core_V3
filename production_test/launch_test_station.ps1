$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$python = Get-Command py -ErrorAction SilentlyContinue

if (-not $python) {
    throw 'Python 3 was not found. Install Python 3 and try again.'
}

$ErrorActionPreference = 'SilentlyContinue'
& py -3 -c "import serial" 2>$null
$serialProbeExitCode = $LASTEXITCODE
$ErrorActionPreference = 'Stop'

if ($serialProbeExitCode -ne 0) {
    Write-Host 'Installing the required pyserial package...'
    & py -3 -m pip install -r (Join-Path $scriptDir 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install pyserial.' }
}

Set-Location $projectDir
$pythonExecutable = (& py -3 -c "import sys; print(sys.executable)").Trim()
$pythonwExecutable = Join-Path (Split-Path -Parent $pythonExecutable) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonwExecutable)) {
    $pythonwExecutable = $pythonExecutable
}

$uiScript = Join-Path $scriptDir 'lor_core_test_station.py'
Start-Process -FilePath $pythonwExecutable -ArgumentList ('"' + $uiScript + '"') -WorkingDirectory $projectDir
