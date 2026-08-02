# Build, Validation, and Release Process

## Version ownership

| Component | Version source | Current production line |
|---|---|---:|
| Windows application/installer | Repository-root `VERSION` | 1.14.x |
| Android application | `android/app/build.gradle` | 1.0.x |
| ESP32 test firmware | `production-test-x.y` in the `.ino` sketch | production-test-1.14 |
| Serial protocol | Firmware and manifests | 1 |

Change a version only when publishing that component. Windows GitHub tags use `v<Windows application version>`.

## Shared firmware package

The Windows release builder is the authoritative firmware packager. It compiles the sketch with the ESP32 `huge_app` partition scheme and produces:

```text
lor-core-v3-firmware-production-test-x.y.zip
lor-core-v3-update-manifest.json
```

The firmware manifest must contain exactly these flash addresses:

| Address | Image |
|---:|---|
| `0x1000` | Bootloader |
| `0x8000` | Partition table |
| `0xe000` | Arduino boot application |
| `0x10000` | Production test application |

The package hash and every image hash are validated by both platform pipelines.

## Windows release

### Builder prerequisites

- Windows 10/11 x64
- Python 3 and the `py` launcher
- `pyinstaller`, `esptool`, and `pyserial`
- Arduino IDE 2.x in its standard location
- Espressif ESP32 Arduino core and FastLED
- NSIS 3.x

### Build

```powershell
py -3 -m pip install --user pyinstaller esptool pyserial
winget install --id NSIS.NSIS --exact
.\installer\build-installer.ps1
```

The builder cleans its generated directories, compiles firmware, creates manifests and hashes, freezes the app/uploader, compiles the NSIS installer, and stages Release assets under `installer/output/release`.

Run deterministic updater tests:

```powershell
py -3 .\installer\test_update_manager.py
```

Publish all three staged assets without renaming them:

```text
LoR_Core_V3_Test_Station_Setup_x.y.z.exe
lor-core-v3-firmware-production-test-x.y.zip
lor-core-v3-update-manifest.json
```

Draft and prerelease GitHub Releases are ignored by installed Windows stations.

## Android release

Android is manually distributed outside Google Play. The APK embeds the verified shared firmware; it does not download replacement firmware at runtime.

### Builder prerequisites

- JDK 17 or newer
- Android SDK Platform 36
- Android Build Tools and Platform Tools
- Android NDK `27.3.13750724`
- CMake 3.22.1
- PowerShell for firmware synchronization

### Synchronize firmware and build

```powershell
.\android\sync-firmware.ps1 -ForceDownload
Set-Location android
.\gradlew.bat lintDebug assembleDebug
```

Without `-ForceDownload`, the synchronizer prefers a locally staged Windows Release package. With it, the script retrieves the latest public Release manifest and firmware ZIP. Both paths validate product, protocol, package SHA-256, per-image SHA-256, filenames, and flash addresses before copying build assets.

The current repository build produces an internally side-loaded APK. For wider production distribution, configure a protected, stable Android signing key and build a release APK. Never commit the keystore or passwords. Every update must use the same signing identity or Android will not install it over the existing app.

### Reference-fixture validation

Before approving a new Android device/hub/cable combination:

1. Confirm USB permission across 20 detach/attach cycles.
2. Confirm automatic ESP32 bootloader entry and all four image writes on at least 20 boards.
3. Complete a known-good pass.
4. Deliberately fail VIN, RF, LED, and one control.
5. Interrupt a test after `TEST_START` and confirm red returns after power cycle.
6. Retest the failed board and confirm a pass clears red.
7. Export CSV and compare its schema/content with Windows.
8. Confirm the Android device can remain powered in its intended USB Host fixture.

## Pull request and CI requirements

The Quality workflow runs on every pull request and on `main`. It validates Python syntax and version formatting, downloads and verifies the shared Android firmware, and builds the Android APK.

Before merging a production change:

- review the complete diff;
- run platform-specific build/lint tests;
- confirm the firmware protocol remains compatible or intentionally version it;
- update operator, architecture, data, troubleshooting, and changelog documentation as applicable;
- require a green Quality check;
- merge through a pull request so the production history remains auditable.

## Post-release checklist

- Install/update Windows on a clean reference PC.
- Install/update Android in place on the reference device.
- Run one complete passing board on each platform.
- Confirm fail-safe red and recovery on at least one platform when firmware is unchanged.
- Verify Windows automatic update metadata and Android embedded firmware versions.
- Verify local history and exported CSV.
- Retain hashes and exact distributed artifacts with the manufacturing release record.
