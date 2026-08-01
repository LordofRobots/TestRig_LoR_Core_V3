# LoR Core V3 Production Test Rig

End-of-line production test software for the Lord of Robots LoR Core V3 robotics controller. The project combines a branded Windows test-station UI with dedicated ESP32 firmware for guided, repeatable board verification.

Current test firmware: `production-test-1.14` (serial protocol version 1).

![Lord of Robots](production_test/assets/lor-logo-white.png)

## What it tests

- Factory ESP32 eFuse MAC identity in canonical format
- Battery input voltage, using a calibrated 20-sample ADC average and a 6–12 V pass range
- Wi-Fi scanning, network count, target/best access point, and RSSI
- Active Bluetooth Low Energy scanning, device count, and strongest RSSI
- Buttons A–D and the user switch using the confirmed LoR Core V3 GPIO mapping
- Four addressable RGB LEDs with operator confirmation
- Persistent pass/fail behavior stored in ESP32 NVS

Every attempted test is appended to a local CSV audit file. The Test History workspace provides searchable run history, measurement cards, and individual check details.

## Install on a production PC

The recommended deployment is the Windows installer:

```text
LoR_Core_V3_Test_Station_Setup_1.14.1.exe
```

Run the setup program as an administrator. It installs the application for all users, creates Lord of Robots Start Menu and desktop shortcuts, and registers an uninstaller in Windows **Installed apps**. The packaged application includes Python, pyserial, esptool, the branded assets, and the verified `production-test-1.14` firmware image. A production PC does not need Python, Arduino IDE, the ESP32 board package, or FastLED.

Windows must recognize the board's WCH CH340/CH341 USB-serial interface. Install the WCH driver if connecting a board does not create a COM port.

Installed production data is stored outside Program Files so application upgrades do not replace test history:

```text
C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\results\lor_core_v3_results.csv
```

Uninstalling the application leaves this production data in place intentionally.

## Automatic updates

The installed application performs one lightweight, non-blocking update check against the public GitHub Releases API shortly after startup. It does not require a GitHub login or keep a background updater running.

- A newer verified firmware package is downloaded once, cached under ProgramData, and used for subsequent board uploads.
- A newer application installer is downloaded only when its version is newer, verified, and launched silently. Windows may show an administrator/UAC prompt because the application is installed for all users.
- Every installer and firmware package must match its published SHA-256 value. Firmware packages also have per-image hashes and an exact approved ESP32 flash layout.
- If GitHub is offline, a download is incomplete, or verification fails, testing continues with the current application and the newest previously verified firmware.

Updates are published as GitHub Release assets, not committed binaries. See [installer/README.md](installer/README.md) for the release procedure and asset names.

## Source-development requirements

- Windows 10 or 11
- Python 3
- Arduino IDE 2.x
- Espressif `esp32` Arduino core 3.x
- FastLED Arduino library
- USB connection to the LoR Core V3

The launcher installs the Python `pyserial` dependency automatically when needed.

## Run from source

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\production_test\launch_test_station.ps1
```

Connect one LoR Core by USB-C. When the board is detected, select **RUN PRODUCTION TEST** and follow the highlighted operator instructions.

The **AUTO-START** toggle is enabled by default for production throughput. When enabled, a newly plugged CH340/WCH LoR Core starts testing after a two-second USB-settle delay. Each connection triggers only once and is re-armed only after the board is unplugged. Set the toggle to **OFF** whenever manual starts are preferred.

The first run compiles the test firmware. Later runs reuse the cached build until the firmware source changes. Firmware upload progress follows the percentage reported by Espressif's uploader.

## Test behavior

On every boot, the LEDs show a brief spatial rainbow vortex across their physical 46 mm square layout. It emerges from black, rotates and blooms across all four corners, then returns to black before the firmware fades into the stored result state:

- Passed or untested: smooth icy-blue spatial orb circling the square
- Failed or interrupted test: solid red, retained across power cycles
- Successful completed test: solid green for two seconds, then a smooth transition to the icy-blue spatial orb

While checking the buttons, the LEDs show yellow for A, green for B, red for C, and blue for D.

The board does not run production measurements or RF scans automatically. VIN, Wi-Fi, BLE, and input snapshots execute only when requested by the UI. Idle firmware work is limited to LED animation, button color feedback, and serial command polling.

## Hardware mapping

| Control | GPIO |
|---|---:|
| Button A | 35 |
| Button B | 39 |
| Button C | 38 |
| Button D | 37 |
| User switch | 36 |
| Battery sense | 34 |
| RGB LED data | 33 |

The production tester follows the confirmed April 2026 firmware mapping. This differs from the older datasheet mapping for buttons B–D and the switch.

## Repository layout

```text
production_test/
  lor_core_test_station.py          Windows production-test UI
  launch_test_station.ps1           Dependency check and launcher
  requirements.txt                  Python dependency specification
  README.md                         Detailed operator documentation
  lor_core_v3_production_test/
    lor_core_v3_production_test.ino ESP32 production-test firmware
  assets/                            Lord of Robots UI branding
docs/
  SERIAL_PROTOCOL.md                Host-to-board command protocol
```

Generated builds, Python caches, machine-specific shortcuts, and production CSV data are intentionally excluded from version control.

The generated installer and its intermediate frozen application are also excluded. See [installer/README.md](installer/README.md) for the repeatable release build.

## Additional documentation

- [Operator and configuration guide](production_test/README.md)
- [Serial command protocol](docs/SERIAL_PROTOCOL.md)
- [Windows installer build and deployment guide](installer/README.md)
