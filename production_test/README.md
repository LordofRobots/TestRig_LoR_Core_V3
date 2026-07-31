# LoR Core V3 Production Test Station

This production station focuses on the LoR-specific circuitry requested for end-of-line testing:

- automatic USB-serial/CH340 detection;
- automatic upload of specialized test firmware;
- ESP32 eFuse MAC as the permanent unique board ID, plus an optional manufacturing serial label;
- battery/input-voltage measurement using a 20-sample average and a 6–12 V tolerance check;
- Wi-Fi scan with network count, target/best SSID, RSSI, and a configurable RSSI floor;
- active Bluetooth Low Energy scan with device count and strongest observed RSSI;
- automatic guided detection of all four buttons and the user switch;
- live button LED feedback: A yellow, B green, C red, and D blue while held;
- a one-second rainbow LED wash on every power-up, followed by either the persistent red-failure state or the normal icy-blue animation;
- an exaggerated icy-blue breathing trail with exactly three LEDs illuminated at a time, with operator confirmation;
- a clear overall PASS/FAIL result;
- a pass indication (solid green for two seconds, then the icy-blue breathing baseline);
- a fail-safe persistent failure indication (solid red, restored after reset or power cycling);
- one append-only row per test attempt in `results/lor_core_v3_results.csv`;
- a searchable **Test History** workspace with a run table on the left and structured board details, measurement cards, and per-check results on the right.

The desktop interface uses the official animated Lord of Robots GIF and flame icon. Test setup and the high-visibility operator instruction banner are contained within **Live Test**; amber highlighting identifies steps that are waiting for operator action. Voltage and RF thresholds remain available under the collapsible **Test parameters** control. During firmware upload, the progress bar follows the main firmware image percentage reported by Espressif's uploader rather than showing an estimated timer.

## Start the station

Double-click `launch_test_station.ps1`, or run:

```powershell
powershell -ExecutionPolicy Bypass -File .\production_test\launch_test_station.ps1
```

The launcher installs `pyserial` if it is missing. Arduino IDE 2.x, the Espressif `esp32` board package, and FastLED must already be installed.

## Operator workflow

1. Power the LoR Core through XT30 with a supply between 6.0 V and 12.0 V, then connect USB-C.
2. Wait for the candidate COM port to appear and the large green **RUN TEST** button to enable.
3. Optionally enter a printed serial number and operator initials. The ESP32 eFuse MAC is always recorded as `board_id`.
4. Click **RUN TEST**. The station compiles and uploads the dedicated firmware automatically. Subsequent boards reuse the verified binary unless the sketch changes, so they go directly to upload.
5. Watch the four LEDs. They should show a fast rainbow for one second and then an icy-blue three-LED breathing trail. Click **LEDs OK** or **LED FAIL**.
6. Follow the large prompt to press and hold buttons A, B, C, and D, then toggle the switch. While held, A lights the LEDs yellow, B green, C red, and D blue. Releasing the button restores the icy-blue breathing animation. No keyboard confirmation is needed; the board detects each transition.
7. Read the large PASS/FAIL result. The CSV row is appended even for test failures and, where possible, station errors.
8. Open **Test History** to search previous boards, filter PASS/FAIL records, and inspect the complete details for any selected test.

At `TEST_START`, the firmware writes a provisional failed state to ESP32 NVS. Only a fully completed pass clears it. This means a failed test, station interruption, reset, or power loss cannot accidentally leave the board showing a normal baseline. On every boot the one-second rainbow runs first; the firmware then reads the stored state and selects locked red or the normal icy-blue trail. Start a new test from the UI to retest a red-latched board; a successful result clears the latch.

## Configuration

- **Fixture VIN / tolerance:** The default pass window is 6.0–12.0 V, represented as a 9.0 V midpoint with a +/-3.0 V tolerance. The calibrated conversion is `volts = ADC * 0.0063492 + 0.697`, based on an 8.000 V fixture reference that previously read 8.382 V.
- **Factory Wi-Fi SSID:** If set, that exact AP must be visible at or above the RSSI floor. If blank, the strongest visible AP is used. A fixed factory AP makes results repeatable.
- **Minimum RSSI:** Defaults to -85 dBm. Establish the real limit from a controlled golden-board study rather than treating this initial value as a final RF specification.
- **Control mapping:** The April 2026 firmware mapping is confirmed as authoritative. It is fixed in the test station so an operator cannot accidentally select the incorrect datasheet mapping.

## Datasheet correction required

| Physical control | Correct GPIO | Incorrect datasheet GPIO |
|---|---:|---:|
| Button A | GPIO35 | GPIO35 |
| Button B | GPIO39 | GPIO36 |
| Button C | GPIO38 | GPIO37 |
| Button D | GPIO37 | GPIO38 |
| User switch | GPIO36 | GPIO39 |

The August 2025 datasheet should be corrected to BTN_A/B/C/D/SW = GPIO35/39/38/37/36. The production tester now uses this mapping exclusively.

## Bluetooth and RSSI scope

The DUT scans both Wi-Fi and BLE over the air. The CSV records Wi-Fi RSSI plus the BLE device count and strongest observed BLE RSSI in the details field. The default BLE pass criterion is at least one received advertisement. For repeatable RF screening, place a fixed "golden" BLE beacon at a controlled distance, then add its identity and an acceptable RSSI window as fixture requirements; ambient devices alone prove radio operation but do not provide calibrated sensitivity testing.

## Result file

The CSV uses one row per board/test attempt and includes:

- UTC timestamp, operator, optional printed serial, eFuse MAC, COM port;
- test-firmware version and basic identity fields;
- measured VIN, the averaged raw ADC count, sample count, and pass/fail;
- Wi-Fi network count, target SSID, RSSI, and pass/fail;
- Bluetooth, every control, LED, and overall pass/fail;
- a compact JSON details field preserving the complete result list.

Do not edit older rows in production. Back up the CSV regularly or move the append operation to a controlled database once multiple stations are running concurrently.
