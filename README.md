# LoR Core V3 Production Test System

<p align="center">
  <img src="production_test/assets/lor-logo-white.png" alt="Lord of Robots" width="620">
</p>

<p align="center">
  <a href="https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/latest"><img alt="Latest Windows release" src="https://img.shields.io/github/v/release/LordofRobots/TestRig_LoR_Core_V3"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Windows%20%7C%20Android-032F82">
  <img alt="Firmware" src="https://img.shields.io/badge/firmware-production--test--1.14-032F82">
  <img alt="License" src="https://img.shields.io/badge/license-All%20rights%20reserved-lightgrey">
</p>

This repository is the complete production test system for the Lord of Robots **LoR Core V3** robotics controller. It contains two production station applications, the dedicated ESP32 test firmware, a shared serial protocol, local CSV traceability, packaging tools, and release/update infrastructure.

The same board receives the same verified firmware and follows the same pass/fail rules whether it is tested from a Windows PC or an Android USB-host device.

## Choose a production station

| | Windows station | Android station |
|---|---|---|
| Best for | Fixed production benches | Portable or compact fixtures |
| Connection | CH340/CH341 virtual COM port | USB-C Host/OTG to CH340 |
| Installation | Self-contained NSIS installer | Manually side-loaded APK |
| Firmware upload | Bundled standalone esptool | Native Espressif serial flasher |
| Test records | ProgramData CSV | Private app CSV with manual export |
| Application updates | Automatic from public GitHub Releases | Manual APK replacement |
| Firmware updates | Verified at runtime from GitHub Releases | Verified and embedded when the APK is built |
| Reference platform | Windows 10/11 x64 | Pixel 6, Android USB Host |

Start with the platform-specific guide:

- **Windows:** [installation, configuration, and operator guide](production_test/README.md)
- **Android:** [installation, USB setup, operation, and APK build guide](android/README.md)

Different Android phones, tablets, hubs, and USB-C cables must be qualified before production use because USB Host power and CH340 control-line behavior vary by device.

## What every test does

1. Detects and opens the LoR Core USB interface.
2. Places the ESP32 into its ROM bootloader and programs the approved four-image firmware package.
3. Reads the canonical factory eFuse MAC address as the permanent board ID.
4. Begins a fail-safe test transaction by provisionally storing **failed** in ESP32 NVS.
5. Measures battery input from a calibrated 20-sample ADC average when that check is enabled.
6. Scans Wi-Fi and records network/RSSI information.
7. Performs an active Bluetooth Low Energy scan.
8. Shows the LED animation and asks the operator to approve it.
9. Guides the operator through buttons A-D and the user switch while detecting each transition automatically.
10. Sends `TEST_PASS` only after every required check passes; otherwise it sends `TEST_FAIL`.
11. Appends one local CSV audit record and displays it in Test History.

## Pass/fail behavior on the board

- **Startup:** a dark-to-dark spatial rainbow presentation always runs first.
- **Normal idle:** the LEDs fade seamlessly into the icy-blue spatial orb.
- **Buttons:** A is yellow, B green, C red, and D blue while held.
- **Pass:** all LEDs show green for two seconds, then return to the icy-blue animation.
- **Fail or interrupted test:** solid red is stored in NVS and returns after every power cycle.
- **Recovery:** a complete passing production test clears the red latch.

The provisional failure state is written at `TEST_START`. A cable disconnect, station crash, reset, or power loss after that point therefore cannot leave an incomplete board looking passed.

## Production test coverage

| Check | Evidence captured | Default criterion |
|---|---|---|
| Identity | eFuse MAC, chip, revision, flash size, firmware | Valid LoR Core V3 protocol handshake |
| Battery input | Calibrated voltage, averaged raw ADC, 20 samples | 6.0-12.0 V |
| Wi-Fi | Visible count, target/best SSID, RSSI | Target or strongest AP at/above configured floor |
| Bluetooth LE | Advertisement count and strongest RSSI | At least one received advertisement |
| RGB LEDs | Rainbow startup and icy-blue animation | Operator approval |
| Buttons A-D | Expected GPIO transition only | Correct individual transition |
| User switch | Expected GPIO transition only | Correct transition |

Android can deliberately skip the battery check through its default-on **Check Battery Voltage** setting. A skipped check is shown as `SKIP`, leaves VIN CSV fields blank, and is excluded from the overall result. Windows always includes the configured VIN check.

## Confirmed LoR Core V3 mapping

| Function | GPIO |
|---|---:|
| Button A | 35 |
| Button B | 39 |
| Button C | 38 |
| Button D | 37 |
| User switch | 36 |
| Battery sense | 34 |
| RGB LED data | 33 |

This April 2026 production mapping supersedes the older datasheet mapping for buttons B-D and the user switch.

## Firmware and trust model

The approved firmware package contains exactly four images at `0x1000`, `0x8000`, `0xe000`, and `0x10000`. Manifests identify the product and protocol and carry a SHA-256 for every image. Both clients reject an incomplete, modified, misaddressed, or wrong-product package.

- Windows ships with a verified fallback package and can activate a newer verified package from a normal public GitHub Release.
- Android's build synchronizer downloads or reuses the same Release package, verifies it, and embeds it in the APK.
- Production stations do not need Arduino IDE or FastLED. Those are release-builder dependencies only.
- Testing continues with the installed/bundled firmware when GitHub or the network is unavailable.

See [System Architecture](docs/ARCHITECTURE.md) and [Serial Protocol](docs/SERIAL_PROTOCOL.md) for the complete design.

## Production records

Every completed or failed production attempt is appended locally. No cloud database or multi-PC synchronization is implemented.

- Windows: `C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\results\lor_core_v3_results.csv`
- Android: private application storage; use **Test History -> Export CSV** to create a portable copy

Windows upgrades and uninstalls preserve ProgramData. Android upgrades preserve app data, but uninstalling the APK removes its private CSV. Manufacturing is responsible for scheduled exports/backups and retention.

See [Data and Traceability](docs/DATA_AND_TRACEABILITY.md) for the schema, skip semantics, privacy guidance, and backup procedure.

## Downloads and installation

### Windows operator installation

**[Download the latest Windows installer](https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/latest)**

The installer includes the UI, Python runtime, pyserial, standalone uploader, branding, and production firmware. It creates desktop and Start Menu shortcuts. The current installer is not Authenticode-signed, so Windows may show an unknown-publisher warning.

### Android operator installation

Android is distributed manually and is not published through Google Play. Build or obtain the approved APK, enable installation from the chosen file source, install it, connect the LoR Core through a USB-C data/OTG path, and grant USB access. Keep the same signing key for every APK update or Android will require uninstalling the old app, which would erase its private history.

See the [Android guide](android/README.md) before deploying an APK to production.

## Repository map

```text
production_test/                     Windows UI, launcher, firmware, and branding
android/                             Native Android USB-host application
installer/                           Windows packaging and GitHub Release builder
docs/ARCHITECTURE.md                 Components, trust boundaries, and state flow
docs/SERIAL_PROTOCOL.md              Host-to-firmware commands and responses
docs/DATA_AND_TRACEABILITY.md        CSV schema, storage, export, and retention
docs/TROUBLESHOOTING.md              Symptom-based recovery procedures
docs/RELEASE_PROCESS.md              Version, build, validation, and release process
.github/workflows/quality.yml        Windows source and Android build validation
VERSION                              Authoritative Windows application version
```

## Documentation index

### Operators and production leads

- [Windows production station](production_test/README.md)
- [Android production station](android/README.md)
- [Data and traceability](docs/DATA_AND_TRACEABILITY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### Developers and release maintainers

- [System architecture](docs/ARCHITECTURE.md)
- [Serial protocol](docs/SERIAL_PROTOCOL.md)
- [Release process](docs/RELEASE_PROCESS.md)
- [Windows installer details](installer/README.md)
- [Android third-party notices](android/THIRD_PARTY_NOTICES.md)
- [Security policy](SECURITY.md)
- [Release history](CHANGELOG.md)

## Support and privacy

Use [GitHub Issues](https://github.com/LordofRobots/TestRig_LoR_Core_V3/issues) for reproducible bugs and documentation problems. Remove board IDs, printed serials, operator names, SSIDs, and CSV production records before attaching logs or screenshots. Report vulnerabilities privately through [GitHub Security Advisories](SECURITY.md).

## License

Copyright © 2026 Lord of Robots. All rights reserved. See [LICENSE](LICENSE). Third-party components retain their own licenses.
