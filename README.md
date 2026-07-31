# LoR Core V3 Production Test Rig

End-of-line production test software for the Lord of Robots LoR Core V3 robotics controller. The project combines a branded Windows test-station UI with dedicated ESP32 firmware for guided, repeatable board verification.

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

## Requirements

- Windows 10 or 11
- Python 3
- Arduino IDE 2.x
- Espressif `esp32` Arduino core 3.x
- FastLED Arduino library
- USB connection to the LoR Core V3

The launcher installs the Python `pyserial` dependency automatically when needed.

## Start the station

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\production_test\launch_test_station.ps1
```

Connect one LoR Core by USB-C. When the board is detected, select **RUN PRODUCTION TEST** and follow the highlighted operator instructions.

The first run compiles the test firmware. Later runs reuse the cached build until the firmware source changes. Firmware upload progress follows the percentage reported by Espressif's uploader.

## Test behavior

On every boot, the LEDs show a one-second rainbow wash. The firmware then reads the stored result state:

- Passed or untested: icy-blue rotating comet animation
- Failed or interrupted test: solid red, retained across power cycles
- Successful completed test: solid green for two seconds, then the icy-blue comet

While checking the buttons, the LEDs show yellow for A, green for B, red for C, and blue for D.

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

## Additional documentation

- [Operator and configuration guide](production_test/README.md)
- [Serial command protocol](docs/SERIAL_PROTOCOL.md)
