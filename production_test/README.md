# LoR Core V3 Windows Production Station

The Windows station is the fixed-bench production client. It is distributed as a self-contained 64-bit installer with the branded UI, standalone uploader, verified firmware, automatic updates, local CSV history, desktop/Start Menu shortcuts, and uninstaller.

Operator PCs do not need Python, Arduino IDE, the ESP32 board package, FastLED, or a separate esptool installation.

## Requirements

- Windows 10 or Windows 11, 64-bit
- Available USB data port
- WCH CH340/CH341 driver (normally installed automatically by Windows)
- LoR Core fixture supply from 6.0 V to 12.0 V through XT30
- Internet is optional; it is used only for a non-blocking update check

## Install

1. Download the latest `LoR_Core_V3_Test_Station_Setup_x.y.z.exe` from [GitHub Releases](https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/latest).
2. Run the installer as an administrator.
3. Choose the installation directory or accept the default.
4. Launch from the desktop or Start Menu shortcut.
5. If Windows does not create a COM port when the board is attached, install/repair the WCH CH340 driver.

The current installer is not Authenticode-signed. Windows SmartScreen may report an unknown publisher. Release assets are delivered over HTTPS and the station verifies update hashes before activation.

Default application location:

```text
C:\Program Files\Lord of Robots\LoR Core V3 Test Station
```

Writable application data:

```text
C:\ProgramData\Lord of Robots\LoR Core V3 Test Station
```

## Operator workflow

1. Apply 6-12 V fixture power through XT30.
2. Connect the LoR Core through USB-C.
3. Wait for the CH340/CH341 COM port and the green **Run Production Test** action.
4. Choose Auto-start:
   - On waits two seconds and starts once for each newly attached board.
   - Off waits for the operator to click Run.
5. Optionally enter the printed board serial and operator identifier.
6. Open **Test Parameters** only when fixture/RF thresholds must change.
7. Start the test and keep power/USB connected.
8. Watch upload progress. The installed station uploads its verified binary package; it does not compile firmware on the production PC.
9. Approve or reject the rainbow startup and icy-blue spatial LED animation.
10. Follow the high-visibility prompts to press/hold A-D and toggle the user switch.
11. Read the final PASS/FAIL result.
12. Use **Test History** to search, filter, and inspect measurements or failures.

## Test Parameters

| Parameter | Default | Meaning |
|---|---:|---|
| Fixture VIN | 9.0 V | Nominal applied battery/input voltage |
| VIN tolerance | 3.0 V | Creates the default 6.0-12.0 V pass window |
| Factory Wi-Fi SSID | blank | Exact AP to require; blank uses strongest visible AP |
| Minimum RSSI | -85 dBm | Lowest accepted Wi-Fi RSSI |

The Windows production sequence always performs VIN. The conversion is:

```text
volts = averaged_ADC * 0.0063492 + 0.697
```

It is based on the corrected 8.000 V fixture reference and uses 20 ADC samples. Establish final VIN and RF thresholds from fixture capability and golden-board studies.

## Guided control mapping

| Prompt | Expected GPIO | LED feedback while held |
|---|---:|---|
| Button A | 35 | Yellow |
| Button B | 39 | Green |
| Button C | 38 | Red |
| Button D | 37 | Blue |
| User switch | 36 | N/A |

The station captures a baseline, waits for the requested transition, rejects unexpected simultaneous GPIO changes, and prompts for button release before continuing.

## Board state and retesting

`TEST_START` provisionally writes failure to ESP32 NVS. Only the final `TEST_PASS` clears it.

- Pass: green for two seconds, then icy blue.
- Failed check: solid red.
- Interrupted test: red after reset/power cycle.
- Retest: connect the red board and run the complete sequence; a pass clears red.

Power-up itself does not run VIN, Wi-Fi, BLE, or input tests. The board performs those checks only when commanded by the station.

## Test History and CSV

The station appends results to:

```text
C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\results\lor_core_v3_results.csv
```

Test History provides a filterable run list and structured details. For long-running stability, the UI displays at most the newest 2,000 records while leaving the full file unchanged. Back up the file according to [Data and Traceability](../docs/DATA_AND_TRACEABILITY.md).

Application upgrades and uninstall operations preserve ProgramData.

## Automatic updates

Shortly after startup, the installed station performs one background query against normal public GitHub Releases.

- Draft and prerelease releases are ignored.
- No GitHub account or embedded token is used.
- Application and firmware versions are compared independently.
- Installer ZIP/package hashes, individual image hashes, product/protocol identity, filenames, and flash addresses are validated.
- New firmware is cached under ProgramData and becomes active only after validation.
- A newer installer is downloaded, verified, and launched for an in-place update.
- Network or validation errors leave the installed app and last verified firmware available.

There is no resident updater service and production testing does not require network access.

## Continuous operation

The animated logo reuses one Tk image buffer and pauses while minimized. Test History loads only when opened and retains at most 2,000 rows in memory. The reference Windows 11 station uses approximately 25 MB of private memory at steady state.

For overnight or multi-shift operation:

- leave Windows power settings appropriate for the fixture;
- prevent automatic USB selective suspend if it causes board disconnects;
- schedule CSV backups;
- close other COM-port applications;
- restart the station during planned maintenance rather than during a test.

## Run from source

Source mode is for development, not production deployment.

Prerequisites:

- Python 3
- Arduino IDE 2.x
- Espressif ESP32 Arduino core 3.x
- FastLED

Launch from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\production_test\launch_test_station.ps1
```

The launcher installs `pyserial` when missing. Source mode compiles firmware when its source is newer than the cached binary. Source-run CSV is written under the ignored repository-level `results` directory.

## Build the installer

The release-builder path is documented in [Release Process](../docs/RELEASE_PROCESS.md) and [Installer README](../installer/README.md). The main command is:

```powershell
.\installer\build-installer.ps1
```

For failures and recovery procedures, see [Troubleshooting](../docs/TROUBLESHOOTING.md).
