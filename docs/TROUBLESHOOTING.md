# Troubleshooting Guide

Use this guide from the first visible symptom. Do not manually clear the board's NVS failure state; a complete passing retest is the intended recovery path.

## Station does not detect the board

### Windows

1. Confirm the USB-C cable carries data, not power only.
2. Confirm the board appears in Windows Device Manager as a WCH CH340/CH341 serial device.
3. Install or repair the WCH driver if no COM port appears.
4. Close Arduino Serial Monitor, terminal programs, and any other process using the COM port.
5. Disconnect and reconnect the physical board. Auto-start re-arms only after detach.

### Android

1. Confirm the phone/tablet supports USB Host/OTG.
2. Use a known-good USB-C data/OTG cable or powered hub.
3. Accept the Android USB permission prompt for the LoR app.
4. Reconnect the board if permission was denied.
5. Test the exact phone, Android version, hub, and cable together; USB power and control lines vary across devices.

## Upload remains at 0% or loader times out

- The progress percentage begins after the ESP32 ROM/stub handshake. A brief 0% period while entering download mode is normal.
- Remove other serial applications.
- Reconnect USB and start a fresh test; the next run rewrites all four images.
- On Android, confirm the device is a WCH/QinHeng CH340 path and that USB permission is still granted.
- If the board entered bootloader but received no image data, it may remain there until reset or the next upload. Reconnecting power or starting a new test is safe.
- Repeated failures on Android usually indicate a cable/hub/device compatibility problem rather than missing Arduino tools.

## Upload reaches 100% but the board does not answer `INFO`

The station waits for the complete startup animation before requesting identity and performs one automatic hard-reset retry.

1. Leave fixture power connected during the post-flash startup.
2. Confirm the startup rainbow appears.
3. Reconnect and repeat the test once.
4. If the issue persists, verify that the firmware manifest and APK/installer came from the same approved release.
5. Capture the exact station message and platform/version before reporting the issue.

## Battery voltage fails

- The accepted default range is 6.0-12.0 V.
- Confirm fixture voltage at the board input with a calibrated meter under test load.
- Inspect XT30 wiring, ground reference, divider components, and GPIO34.
- The firmware averages 20 ADC measurements and applies `volts = ADC * 0.0063492 + 0.697`.
- Review `raw_adc` in the result details. A stable but offset raw value suggests calibration/divider tolerance; a noisy value suggests connection, ground, or ADC interference.
- Android can skip this check only when the production procedure explicitly permits it. A skip is not evidence that the battery circuit passed.

## Wi-Fi fails or RSSI is weak

- If a Factory Wi-Fi SSID is configured, spelling and case must match the access point.
- Place a fixed factory access point at a controlled location for repeatable screening.
- The default floor is -85 dBm; establish the real production threshold through a golden-board study.
- Metal fixtures, the operator's hand, USB hubs, and nearby electronics can alter results.
- Blank SSID evaluates the strongest visible access point and proves basic radio operation, not calibrated receiver sensitivity.

## Bluetooth fails

The board performs an active three-second BLE scan. The default pass requires at least one advertisement.

1. Place a known BLE beacon near the fixture.
2. Confirm the beacon is advertising rather than merely paired.
3. Repeat away from RF shielding or crowded USB hardware.
4. Use a controlled beacon and distance if RSSI is part of the manufacturing specification.

## LED check fails

- Confirm all four corners participate in the startup rainbow and icy-blue spatial animation.
- Physical order is top-left LED 1, bottom-left LED 2, bottom-right LED 3, top-right LED 4.
- Reject the LED check for a missing channel, wrong color, damaged LED, discontinuity, or visibly incorrect spatial order.
- Button feedback should show A yellow, B green, C red, and D blue while held.

## Button or switch check fails

The expected mapping is A/B/C/D/SW = GPIO35/39/38/37/36. Older datasheet mappings are not used.

- Press only the requested control.
- Hold each button until the station detects it, then release when prompted.
- Toggle the switch to the opposite state from its captured baseline.
- A result listing multiple changed GPIOs suggests shorts, incorrect pull states, or cross-wiring.

## Board is locked red

Red means the last production transaction did not complete successfully. It survives resets and power cycles by design.

1. Correct the failed hardware or fixture condition.
2. Connect the board to either production station.
3. Run the complete required test sequence.
4. A pass shows green for two seconds and clears the stored latch.

Do not treat a power cycle, firmware upload alone, or a skipped required check as a pass.

## CSV/history problem

### Windows

- Confirm the current user can modify the ProgramData application directory.
- Preserve the original CSV before manual inspection.
- Test History displays the newest 2,000 rows but the file may contain more.

### Android

- Export through Test History and Android's document picker.
- Do not uninstall or clear storage before export.
- Install updates with the same package ID and signing key so Android performs an in-place upgrade.

## Reporting a reproducible issue

Include station platform, application version, firmware version, exact message, connection hardware, and sanitized reproduction steps. Remove eFuse MACs, printed serials, operators, SSIDs, and production CSV content. Use the private process in [SECURITY.md](../SECURITY.md) for vulnerabilities.

