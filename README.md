# LoR Core V3 Production Test Rig

<p align="center">
  <img src="production_test/assets/lor-logo-white.png" alt="Lord of Robots" width="620">
</p>

<p align="center">
  <a href="https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/LordofRobots/TestRig_LoR_Core_V3"></a>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D4">
  <img alt="Firmware" src="https://img.shields.io/badge/firmware-production--test--1.14-032F82">
  <img alt="License" src="https://img.shields.io/badge/license-All%20rights%20reserved-lightgrey">
</p>

A production-ready Windows test station and dedicated ESP32 firmware for guided, repeatable end-of-line verification of the Lord of Robots **LoR Core V3** robotics controller.

An Android USB-host companion is also under engineering validation. It lives beside the Windows station and consumes the same hash-verified production firmware package and serial protocol.

## Download

**[Download LoR Core V3 Test Station 1.14.2](https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/latest/download/LoR_Core_V3_Test_Station_Setup_1.14.2.exe)**

The self-contained installer includes the branded desktop UI, Python runtime, pyserial, esptool uploader, and verified `production-test-1.14` firmware. Production PCs do **not** require Python, Arduino IDE, the ESP32 board package, or FastLED.

> Windows SmartScreen may identify the current installer as an unknown publisher because it is not yet Authenticode-signed. Release files are delivered over HTTPS and verified against SHA-256 values in the published update manifest.

## Release status

| Component | Version | Status |
|---|---:|---|
| Windows test station | 1.14.2 | Production |
| Board test firmware | production-test-1.14 | Production |
| Serial protocol | 1 | Stable |
| Installer | NSIS 3.x | Free for commercial use |

## Test coverage

- ESP32 factory eFuse MAC identity in canonical format
- Battery input voltage using a calibrated 20-sample ADC average and a 6–12 V pass range
- Raw averaged battery ADC value for fixture diagnostics
- Wi-Fi scanning, visible-network count, target/best access point, and RSSI
- Active Bluetooth Low Energy scanning, device count, and strongest RSSI
- Buttons A–D and the user switch using the confirmed LoR Core V3 mapping
- Four addressable RGB LEDs with operator confirmation
- Persistent pass/fail behavior stored in ESP32 NVS

Every attempted run appends one row to the CSV audit log. The Test History workspace provides searchable runs, measurement cards, board metadata, and per-check results.

## Operator quick start

1. Install the latest Windows release as an administrator.
2. Power the LoR Core through XT30 with a 6–12 V supply.
3. Connect USB-C and wait for the station to detect the WCH CH340/CH341 COM port.
4. Leave **AUTO-START** enabled for production throughput, or disable it for manual starts.
5. Follow the highlighted prompts for the LED, button, and switch checks.
6. Confirm the final PASS or FAIL result and, if needed, review the saved record under **Test History**.

The board shows green for two seconds after a pass and then returns to its icy-blue spatial animation. A failed or interrupted test latches solid red across power cycles until a complete retest passes.

## Hardware mapping

| Function | GPIO |
|---|---:|
| Button A | 35 |
| Button B | 39 |
| Button C | 38 |
| Button D | 37 |
| User switch | 36 |
| Battery sense | 34 |
| RGB LED data | 33 |

This confirmed April 2026 mapping supersedes the older datasheet mapping for buttons B–D and the user switch.

## Automatic updates

The installed station performs one lightweight, non-blocking check against this repository's public GitHub Releases shortly after startup.

- New firmware is downloaded only when its version is newer, verified, and cached under ProgramData.
- New application installers are downloaded only when the application version increases.
- Installer ZIP/package hashes, per-image firmware hashes, and the approved ESP32 flash layout are validated before use.
- Draft and prerelease GitHub Releases are ignored.
- Network, download, or validation failures fall back to the installed application and newest previously verified firmware.

No GitHub login, embedded access token, resident update service, or Arduino toolchain is required on a production station.

## Production data

Installed audit data is stored outside Program Files:

```text
C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\results\lor_core_v3_results.csv
```

Application upgrades and uninstall operations deliberately preserve this directory. Back up the CSV as part of the manufacturing data-retention process.

## Development

Source development requires Windows 10/11, Python 3, Arduino IDE 2.x, Espressif's ESP32 Arduino core 3.x, and FastLED.

Run the station from source:

```powershell
powershell -ExecutionPolicy Bypass -File .\production_test\launch_test_station.ps1
```

Build the self-contained application, free NSIS installer, firmware package, and GitHub Release manifest:

```powershell
.\installer\build-installer.ps1
```

The root [`VERSION`](VERSION) file is the authoritative desktop application version. Firmware versioning remains embedded in the production-test sketch and is extracted automatically during the release build.

### Android engineering preview

The native Android client supports CH340 USB detection, ESP32 firmware upload, the guided production workflow, local CSV history, and CSV export. Build and fixture-validation instructions are in the [Android guide](android/README.md). The Windows station remains the production-qualified reference until the Android USB flashing path passes the documented real-hardware checklist.

## Repository structure

```text
production_test/
  lor_core_test_station.py           Windows production-test UI
  launch_test_station.ps1            Source launcher and dependency check
  lor_core_v3_production_test/       Dedicated ESP32 test firmware
  assets/                             Lord of Robots branding
installer/
  build-installer.ps1                Repeatable release builder
  LoR_Core_V3_Test_Station.nsi       Free NSIS installer definition
  test_update_manager.py             Deterministic update validation
android/
  app/                                Native USB-host test-station APK
  sync-firmware.ps1                   Shared Release firmware synchronizer
docs/
  ARCHITECTURE.md                     System and trust architecture
  SERIAL_PROTOCOL.md                 Host-to-board serial protocol
```

Generated builds, local CSV records, Python caches, shortcuts, and release output are excluded from version control.

## Documentation

- [Operator and configuration guide](production_test/README.md)
- [System architecture](docs/ARCHITECTURE.md)
- [Serial command protocol](docs/SERIAL_PROTOCOL.md)
- [Installer and release guide](installer/README.md)
- [Android build and validation guide](android/README.md)
- [Release history](CHANGELOG.md)
- [Security policy](SECURITY.md)

## Support

Use [GitHub Issues](https://github.com/LordofRobots/TestRig_LoR_Core_V3/issues) for reproducible bugs and documentation problems. Remove board identifiers, private network details, operator information, and manufacturing records before attaching diagnostics. Report suspected vulnerabilities privately through the process in [SECURITY.md](SECURITY.md).

## License

Copyright © 2026 Lord of Robots. All rights reserved. See [LICENSE](LICENSE). Third-party tools and libraries retain their respective licenses; in particular, NSIS permits commercial use under its zlib/libpng-based license.
