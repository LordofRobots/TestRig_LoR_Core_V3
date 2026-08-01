$ErrorActionPreference = 'Stop'

function Write-JsonFile([object]$Value, [string]$Path, [int]$Depth) {
    $json = $Value | ConvertTo-Json -Depth $Depth
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json, $utf8NoBom)
}

$installerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $installerDir
$outputDir = Join-Path $installerDir 'output'
$workDir = Join-Path $installerDir 'work'
$toolOutputDir = Join-Path $workDir 'tools'
$firmwareStageDir = Join-Path $workDir 'firmware-package'
$releaseDir = Join-Path $outputDir 'release'
$firmwareBuildDir = Join-Path $projectDir 'build\lor_core_v3_production_test'
$appVersion = '1.14.0'
$arduinoCli = 'C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe'
$isccCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe'
)
$iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python 3 with the Windows py launcher is required to build the installer.'
}
if (-not (Test-Path -LiteralPath $arduinoCli)) {
    throw 'Arduino IDE 2.x was not found in its standard installation directory.'
}
if (-not $iscc) {
    throw 'Inno Setup 6 was not found. Install it with: winget install JRSoftware.InnoSetup'
}

& py -3 -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller is required: py -3 -m pip install pyinstaller' }
& py -3 -c 'import esptool' *> $null
if ($LASTEXITCODE -ne 0) { throw 'esptool is required: py -3 -m pip install esptool' }

$resolvedProject = [System.IO.Path]::GetFullPath($projectDir)
$resolvedOutput = [System.IO.Path]::GetFullPath($outputDir)
$resolvedWork = [System.IO.Path]::GetFullPath($workDir)
if (-not $resolvedOutput.StartsWith($resolvedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installer output path escaped the project directory.'
}
if (-not $resolvedWork.StartsWith($resolvedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installer work path escaped the project directory.'
}
if (Test-Path -LiteralPath $outputDir) { Remove-Item -LiteralPath $outputDir -Recurse -Force }
if (Test-Path -LiteralPath $workDir) { Remove-Item -LiteralPath $workDir -Recurse -Force }
New-Item -ItemType Directory -Path $outputDir, $workDir, $toolOutputDir, $firmwareStageDir, $releaseDir -Force | Out-Null

Write-Host 'Compiling production firmware...'
& $arduinoCli compile --fqbn esp32:esp32:esp32 --board-options PartitionScheme=huge_app `
    (Join-Path $projectDir 'production_test\lor_core_v3_production_test') `
    --build-path $firmwareBuildDir
if ($LASTEXITCODE -ne 0) { throw 'Firmware compilation failed.' }

$bootApp = Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA 'Arduino15\packages\esp32\hardware\esp32') `
    -Recurse -Filter boot_app0.bin | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $bootApp) { throw 'boot_app0.bin was not found in the installed ESP32 Arduino core.' }

$firmwareSourcePath = Join-Path $projectDir 'production_test\lor_core_v3_production_test\lor_core_v3_production_test.ino'
$firmwareSource = Get-Content -Raw -LiteralPath $firmwareSourcePath
$firmwareVersionMatch = [regex]::Match($firmwareSource, 'production-test-\d+(?:\.\d+)+')
if (-not $firmwareVersionMatch.Success) { throw 'The firmware version could not be read from the sketch.' }
$firmwareVersion = $firmwareVersionMatch.Value

$firmwareInputs = [ordered]@{
    '0x1000' = Join-Path $firmwareBuildDir 'lor_core_v3_production_test.ino.bootloader.bin'
    '0x8000' = Join-Path $firmwareBuildDir 'lor_core_v3_production_test.ino.partitions.bin'
    '0xe000' = $bootApp.FullName
    '0x10000' = Join-Path $firmwareBuildDir 'lor_core_v3_production_test.ino.bin'
}
$firmwareFiles = @()
foreach ($entry in $firmwareInputs.GetEnumerator()) {
    $destination = Join-Path $firmwareStageDir ([System.IO.Path]::GetFileName($entry.Value))
    Copy-Item -LiteralPath $entry.Value -Destination $destination -Force
    $firmwareFiles += [ordered]@{
        address = $entry.Key
        name = [System.IO.Path]::GetFileName($destination)
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash
    }
}
$firmwareAssetName = "lor-core-v3-firmware-$firmwareVersion.zip"
$firmwareArchive = Join-Path $releaseDir $firmwareAssetName
$firmwareImagePaths = Get-ChildItem -LiteralPath $firmwareStageDir -Filter '*.bin' | Select-Object -ExpandProperty FullName
Compress-Archive -LiteralPath $firmwareImagePaths -DestinationPath $firmwareArchive -CompressionLevel Optimal
$firmwareManifest = [ordered]@{
    schema = 1
    product = 'LoR Core V3'
    version = $firmwareVersion
    protocol = 1
    package_asset = $firmwareAssetName
    package_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $firmwareArchive).Hash
    files = $firmwareFiles
}
$firmwareManifestPath = Join-Path $firmwareStageDir 'lor-core-v3-firmware-manifest.json'
Write-JsonFile $firmwareManifest $firmwareManifestPath 6

Write-Host 'Building bundled ESP32 uploader...'
& py -3 -m PyInstaller --noconfirm --clean --onefile --console `
    --name lor_esptool --collect-all esptool --distpath $toolOutputDir `
    --workpath (Join-Path $workDir 'esptool') --specpath $workDir `
    (Join-Path $installerDir 'esptool_entry.py')
if ($LASTEXITCODE -ne 0) { throw 'Bundled uploader build failed.' }

$appDist = Join-Path $outputDir 'app'
$assetSource = Join-Path $projectDir 'production_test\assets'
$uiSource = Join-Path $projectDir 'production_test\lor_core_test_station.py'
Write-Host 'Building desktop application...'
& py -3 -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name 'LoR Core V3 Test Station' `
    --icon (Join-Path $assetSource 'lor-test-station.ico') `
    --distpath $appDist --workpath (Join-Path $workDir 'app') --specpath $workDir `
    --add-data "$assetSource;production_test/assets" `
    --add-binary "$(Join-Path $toolOutputDir 'lor_esptool.exe');tools" `
    --add-data "$(Join-Path $firmwareStageDir 'lor_core_v3_production_test.ino.bin');firmware" `
    --add-data "$(Join-Path $firmwareStageDir 'lor_core_v3_production_test.ino.bootloader.bin');firmware" `
    --add-data "$(Join-Path $firmwareStageDir 'lor_core_v3_production_test.ino.partitions.bin');firmware" `
    --add-data "$(Join-Path $firmwareStageDir 'boot_app0.bin');firmware" `
    --add-data "$firmwareManifestPath;firmware" `
    $uiSource
if ($LASTEXITCODE -ne 0) { throw 'Desktop application build failed.' }

Write-Host 'Compiling Windows installer...'
& $iscc (Join-Path $installerDir 'LoR_Core_V3_Test_Station.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }

$setup = Get-ChildItem -LiteralPath $outputDir -Filter 'LoR_Core_V3_Test_Station_Setup_*.exe' |
    Select-Object -First 1
if (-not $setup) { throw 'Installer output was not created.' }
$updateManifest = [ordered]@{
    schema = 1
    product = 'LoR Core V3 Test Station'
    app = [ordered]@{
        version = $appVersion
        asset = $setup.Name
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup.FullName).Hash
    }
    firmware = $firmwareManifest
}
Write-JsonFile $updateManifest (Join-Path $releaseDir 'lor-core-v3-update-manifest.json') 8
Copy-Item -LiteralPath $setup.FullName -Destination (Join-Path $releaseDir $setup.Name) -Force
Write-Host "Installer created: $($setup.FullName)"
Write-Host "GitHub release assets: $releaseDir"
