# LoR Core V3 Android Production Station

The Android application is the portable production client for the LoR Core V3. It connects directly through Android USB Host/OTG, programs the same approved ESP32 firmware used by Windows, guides the complete test, stores local history, and exports Windows-compatible CSV records.

Version **1.0.0** is the production baseline validated on the Pixel 6 reference path. Qualify every different phone/tablet, Android version, hub, and cable combination before manufacturing use.

## Platform requirements

- Android 8.0 / API 26 or newer
- ARMv7 or ARM64 processor
- USB Host/OTG support
- Portrait phone or tablet display
- USB-C data/OTG cable or a powered USB-C hub
- LoR Core fixture supply from 6.0 V to 12.0 V through XT30
- WCH/QinHeng CH340 USB interface on the board

No root access, Arduino IDE, Python, esptool command-line installation, or Android USB driver is required on the operator device.

## Installation and updates

The app is manually distributed and is not published through Google Play.

1. Obtain the approved APK from the internal manufacturing release.
2. On Android, allow installation from the file manager or browser used to open it.
3. Open the APK and install **LoR Core V3 Test Station**.
4. Launch it once and confirm the header reads **Production Testing**.
5. Connect the board and grant the app USB access when Android asks.

Install future APKs over the existing app. They must use the same package ID and signing key. Uninstalling the app or clearing its storage deletes the private test-history CSV, so export records first.

The repository's standard debug build is suitable for controlled internal deployment and hardware validation. Before distributing broadly, configure a protected stable release key as described in [Release Process](../docs/RELEASE_PROCESS.md). Never commit a keystore or password.

## Operator workflow

1. Apply 6-12 V fixture power to the LoR Core.
2. Connect the LoR Core to the Android device through the qualified USB Host path.
3. Grant USB access if prompted and wait for **LoR CORE READY**.
4. Choose Auto-start:
   - On starts one test for each newly attached physical board.
   - Off requires **Run Production Test**.
5. Expand **Test Setup** when configuration is required.
6. Optionally enter operator and printed board label values.
7. Leave **Check Battery Voltage** enabled for the normal complete test. Disable it only when the approved manufacturing procedure intentionally omits VIN.
8. Set Fixture VIN and Tolerance. Defaults 9.0 and 3.0 create the 6.0-12.0 V window.
9. Optionally enter the exact factory Wi-Fi SSID and set the RSSI floor (default -85 dBm).
10. Start the test and keep USB and fixture power connected through upload and startup.
11. Approve or reject the visible rainbow/icy-blue LED presentation.
12. Follow the high-visibility prompts for buttons A-D and the switch.
13. Confirm the final PASS/FAIL result and review Test History.

During upload, the progress bar reports bytes written across the actual firmware images. It may briefly remain at 0% while the app enters the ESP32 ROM bootloader and uploads the loader stub.

## Test Setup controls

| Control | Purpose |
|---|---|
| Operator | Optional initials/name stored in CSV |
| Board serial / label | Optional printed manufacturing identifier |
| Check Battery Voltage | Default-on VIN check; disabled means `SKIP` |
| Fixture VIN | Nominal fixture voltage |
| Tolerance | Plus/minus voltage tolerance |
| Factory Wi-Fi SSID | Optional exact AP to require |
| Minimum RSSI | Lowest accepted Wi-Fi RSSI in dBm |

The eFuse MAC is always collected as `board_id`; it does not depend on the optional label.

## Production sequence

- Android USB permission and CH340 open
- Native ESP32 ROM/stub synchronization
- Four-image erase/write with MD5 verification
- Hard reset and startup wait
- LoR Core identity/protocol handshake
- Fail-safe `TEST_START`
- Optional 20-sample VIN and raw ADC
- Wi-Fi scan/RSSI
- Active BLE scan
- Operator LED approval
- Automatic buttons A-D and switch transitions
- Persistent `TEST_PASS` or `TEST_FAIL`
- Local CSV append and Test History update

The native uploader is based on Espressif ESP Serial Flasher 1.11.0 and a CH340 Android transport. The APK contains only ARM ABIs and supports Android 16 KB memory pages.

## Results and export

Test History shows saved runs and the detailed data for the selected board. The working CSV is in private application storage and survives normal in-place updates.

To create a backup:

1. Open **Test History**.
2. Select **Export CSV**.
3. Choose a controlled manufacturing location in Android's document picker.
4. Verify the newest board appears in the exported file.

See [Data and Traceability](../docs/DATA_AND_TRACEABILITY.md) before operating multiple local stations.

## Battery-check skip behavior

When **Check Battery Voltage** is off:

- VIN and Tolerance inputs are disabled visually;
- the firmware receives no `VIN` command;
- live results show `SKIP` rather than PASS or FAIL;
- CSV `vin_volts` and `vin_pass` remain blank;
- VIN is excluded from the overall result.

This option accommodates fixtures that cannot provide the battery input. It must not be used to hide a failed battery-sense circuit when VIN is required by the production procedure.

## Build from source

### Prerequisites

- JDK 17 or newer
- Android SDK Platform 36
- Android Platform Tools
- Android NDK `27.3.13750724`
- CMake 3.22.1

Android Studio can provide these components, but it is not required on the production operator device.

### Synchronize the shared firmware

From the repository root:

```powershell
.\android\sync-firmware.ps1 -ForceDownload
```

The script downloads the latest public Release manifest and firmware package, checks SHA-256 values and the exact flash layout, and stages the verified images as ignored build assets. Omit `-ForceDownload` to prefer a package already built under `installer/output/release`.

### Build and lint

```powershell
Set-Location android
.\gradlew.bat lintDebug assembleDebug
```

The APK is written to:

```text
android\app\build\outputs\apk\debug\app-debug.apk
```

Install through ADB when developing:

```powershell
adb install -r .\app\build\outputs\apk\debug\app-debug.apk
```

## Qualification checklist

Before approving any new Android fixture combination:

1. Repeat attach/permission/detach at least 20 times.
2. Flash at least 20 boards without manual BOOT/RESET input.
3. Confirm 0-100% progress and post-flash identity on every board.
4. Run a complete known-good pass.
5. Deliberately fail each test category.
6. Interrupt after `TEST_START`, power cycle, and confirm persistent red.
7. Complete a pass and confirm red clears after the two-second green indication.
8. Export CSV and compare it with the Windows schema.
9. Run the device for a full shift and confirm charging/power/thermal stability.

## Known operational differences from Windows

- Android application updates are manual; Windows checks public GitHub Releases automatically.
- Android embeds firmware at APK build time; Windows can activate a newer verified firmware package at runtime.
- Android data requires explicit export; Windows data is directly available under ProgramData.
- Android offers an optional VIN toggle; Windows includes VIN in every production sequence.
- Android USB behavior depends on the qualified device/hub/cable combination.

For symptom-based recovery, see [Troubleshooting](../docs/TROUBLESHOOTING.md).
