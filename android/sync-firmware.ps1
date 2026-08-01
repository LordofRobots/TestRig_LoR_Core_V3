[CmdletBinding()]
param([switch]$ForceDownload)

$ErrorActionPreference = 'Stop'
$androidDir = $PSScriptRoot
$projectRoot = Split-Path -Parent $androidDir
$assetDir = Join-Path $androidDir 'app\src\main\assets\firmware'
$releaseDir = Join-Path $projectRoot 'installer\output\release'
$localManifest = Join-Path $releaseDir 'lor-core-v3-update-manifest.json'
$api = 'https://api.github.com/repos/LordofRobots/TestRig_LoR_Core_V3/releases/latest'
$headers = @{ Accept = 'application/vnd.github+json'; 'User-Agent' = 'LoR-Core-V3-Android-Build' }

New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
if (-not $ForceDownload -and (Test-Path -LiteralPath $localManifest)) {
    $updateManifest = Get-Content -Raw -LiteralPath $localManifest | ConvertFrom-Json
    $package = Join-Path $releaseDir $updateManifest.firmware.package_asset
} else {
    $release = Invoke-RestMethod -Uri $api -Headers $headers
    $manifestAsset = $release.assets | Where-Object name -eq 'lor-core-v3-update-manifest.json' | Select-Object -First 1
    if (-not $manifestAsset) { throw 'The latest release has no Android-compatible update manifest.' }
    $downloadRoot = Join-Path ([IO.Path]::GetTempPath()) 'lor-core-v3-android-firmware'
    New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
    $downloadedManifest = Join-Path $downloadRoot 'lor-core-v3-update-manifest.json'
    Invoke-WebRequest -Uri $manifestAsset.browser_download_url -Headers $headers -OutFile $downloadedManifest
    $updateManifest = Get-Content -Raw -LiteralPath $downloadedManifest | ConvertFrom-Json
    $packageAsset = $release.assets | Where-Object name -eq $updateManifest.firmware.package_asset | Select-Object -First 1
    if (-not $packageAsset) { throw "Firmware asset not found: $($updateManifest.firmware.package_asset)" }
    $package = Join-Path $downloadRoot $packageAsset.name
    Invoke-WebRequest -Uri $packageAsset.browser_download_url -Headers $headers -OutFile $package
}

if (-not (Test-Path -LiteralPath $package)) { throw "Firmware package not found: $package" }
if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $updateManifest.firmware.package_sha256) {
    throw 'Firmware package SHA-256 validation failed.'
}

$extractDir = Join-Path ([IO.Path]::GetTempPath()) ("lor-core-v3-firmware-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $extractDir | Out-Null
try {
    Expand-Archive -LiteralPath $package -DestinationPath $extractDir
    $approved = @('0x1000', '0x8000', '0xe000', '0x10000')
    $addresses = @($updateManifest.firmware.files | ForEach-Object address)
    if (Compare-Object $approved $addresses) { throw 'Firmware flash layout is not approved for LoR Core V3.' }
    Get-ChildItem -LiteralPath $assetDir -File | Where-Object Name -ne '.gitkeep' | Remove-Item -Force
    foreach ($item in $updateManifest.firmware.files) {
        $source = Join-Path $extractDir $item.name
        if (-not (Test-Path -LiteralPath $source)) { throw "Missing firmware image: $($item.name)" }
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $item.sha256) {
            throw "Firmware image SHA-256 validation failed: $($item.name)"
        }
        Copy-Item -LiteralPath $source -Destination (Join-Path $assetDir $item.name)
    }
    $updateManifest.firmware | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $assetDir 'lor-core-v3-firmware-manifest.json') -Encoding utf8
} finally {
    if (Test-Path -LiteralPath $extractDir) { Remove-Item -LiteralPath $extractDir -Recurse -Force }
}
Write-Host "Android firmware synchronized: $($updateManifest.firmware.version)"
