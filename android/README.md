# LoR Core V3 Android Test Station

The Android client is a lightweight, native companion to the Windows production station. It uses the same board firmware, serial protocol, production checks, pass/fail behavior, and CSV field schema.

## Current status

Version `0.1.0` is an engineering preview. The APK builds, installs, and runs in portrait mode on a Pixel 6. Real-device validation has confirmed Android USB-host operation, CH340 detection, persistent USB permission, automatic ESP32 loader entry, four-image flashing, byte-accurate progress, MD5 verification, and target reset. The complete guided production workflow must still pass the production-validation checklist before production use.

## Device requirements

- Android 8.0 (API 26) or newer
- USB Host/OTG support
- Portrait display on a phone or tablet
- USB-C data/OTG cable or powered USB-C hub
- LoR Core fixture power of 6–12 V through XT30

The app recognizes the WCH/QinHeng CH340 family used by the LoR Core. Android asks the operator to authorize USB access. No root access or system USB driver is required.

## Install the engineering APK

1. Copy `app/build/outputs/apk/debug/app-debug.apk` to the Android device.
2. Allow installation from the selected file-manager source when Android requests it.
3. Install **LoR Core V3 Test Station**.
4. Connect one LoR Core with a USB-C OTG/data connection.
5. Grant USB access and follow the live-test prompts.

The debug APK is intended for fixture validation. A permanent Android signing key must be configured before publishing a production APK.

## Build

From PowerShell at the repository root:

```powershell
.\android\sync-firmware.ps1
cd android
.\gradlew.bat assembleDebug
```

`sync-firmware.ps1` prefers the locally built Windows release package. With `-ForceDownload`, it retrieves the latest public GitHub Release manifest and firmware ZIP. It validates the package SHA-256, exact four-image flash layout, and every image SHA-256 before placing build-only copies in Android assets.

The synchronized binaries and APK outputs are intentionally ignored by Git. GitHub Releases remain the shared firmware source for both platforms.

## Implemented workflow

- CH340 attach/detach detection and Android USB permission
- Optional one-shot auto-start after a newly connected board is authorized
- Espressif ESP Serial Flasher v1.11.0 with loader-stub upload, byte-accurate progress, retries, and MD5 verification
- Hash-verified `production-test-1.14` four-image firmware package
- Board eFuse MAC identity and metadata
- Twenty-sample VIN and raw ADC result
- Battery-voltage check toggle in Test Setup, enabled by default
- Board-side Wi-Fi and BLE scanning with RSSI data
- Guided LED, buttons A–D, and user-switch checks
- Persistent red failure latch and green pass confirmation
- Local CSV history using the Windows-compatible field order
- Compact portrait live-test UI with expandable setup and scrolling test results
- Always-visible primary Run action above Test Setup when the station is idle
- Stacked history list/details UI optimized for portrait use, plus Android document-provider CSV export
- 16 KB Android memory-page compatibility and ARM-only release packaging

## Production-validation checklist

Before replacing a Windows station, validate on the exact tablet/hub/cable combination:

1. CH340 USB permission survives repeated plug/unplug cycles.
2. DTR/RTS enters the ESP32 ROM bootloader automatically on at least 20 boards.
3. All four images flash and boot without manual BOOT/RESET input.
4. A full pass, deliberate failure, unplug during test, and power cycle produce the expected LED latch.
5. CSV export opens correctly in the chosen manufacturing archive workflow.
6. The tablet can remain charged while acting as USB host.

## Data location

The working CSV is kept in Android private application storage and survives ordinary app updates. Use **Export CSV** to write a copy through Android's document picker. Uninstalling the APK removes private application data, so export or back up results first.
