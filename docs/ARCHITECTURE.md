# System Architecture

## Purpose

The LoR Core V3 Production Test Rig separates operator workflow, board-side hardware access, release packaging, and manufacturing records. Production PCs run a self-contained Windows application; build tools remain confined to development and release-builder machines.

## Components

| Component | Responsibility |
|---|---|
| Windows test station | Board detection, firmware upload, guided workflow, result evaluation, history, and updates |
| ESP32 production firmware | LoR-specific measurements, RF scans, control input detection, LED behavior, and persistent failure state |
| Bundled esptool | Programs the approved ESP32 flash image set without Arduino IDE |
| NSIS installer | Installs the frozen application for all users and preserves ProgramData records |
| GitHub Release | Publishes the installer, firmware ZIP, and hash-verified update manifest |
| CSV audit log | Stores one append-only row for every attempted production test |

## Production flow

```text
USB connection
    |
CH340/WCH COM-port detection
    |
Verified production firmware upload
    |
Serial identity and protocol handshake
    |
VIN -> Wi-Fi -> BLE -> LEDs -> buttons/switch
    |
TEST_PASS or TEST_FAIL persisted on the board
    |
Append CSV record and display result history
```

The board never runs VIN, Wi-Fi, BLE, or production input checks merely because it powered up. These operations execute only after explicit serial commands from the station. Idle firmware work is limited to serial polling, button-color feedback, and LED presentation.

## Failure safety

`TEST_START` provisionally writes failure to ESP32 NVS before measurements begin. Only `TEST_PASS` clears the latch. A failed check, application crash, power interruption, or unplugged board therefore returns to locked red after the next startup presentation rather than appearing untested or passed.

## Data locations

| Data | Installed location | Upgrade behavior |
|---|---|---|
| Application runtime | `C:\Program Files\Lord of Robots\LoR Core V3 Test Station` | Replaced cleanly |
| Test results | `C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\results` | Preserved |
| Firmware cache | `C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\firmware` | Preserved and revalidated |
| Downloaded updates | `C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\updates` | Preserved |

## Update sequence

1. The frozen application starts from its bundled, verified firmware package.
2. A daemon thread queries public, published GitHub Releases once after startup.
3. Draft and prerelease releases are ignored.
4. The manifest identity and version are validated.
5. New packages are downloaded only when their version is greater than the active version.
6. Package and per-image SHA-256 values are verified before activation.
7. Firmware ZIP paths and the four approved flash addresses are validated.
8. A failed check leaves the installed application and last verified firmware active.

The updater carries no GitHub credential and runs no resident service. Repository availability is not required to continue production testing.

## Version ownership

- `VERSION` is the authoritative Windows application version.
- The firmware sketch declares `production-test-x.y` and protocol version 1.
- `build-installer.ps1` reads both versions, builds all artifacts, and generates the release manifest.
- GitHub Release tags use `v<application-version>`.

## Resource profile

The UI uses Tkinter and a one-directory frozen Python runtime. The animated logo reuses a single image buffer and pauses while minimized. Test History is lazy-loaded and retains at most 2,000 display records in memory; the complete audit CSV remains on disk. Verified steady-state private memory is approximately 25 MB on the reference Windows 11 station.
