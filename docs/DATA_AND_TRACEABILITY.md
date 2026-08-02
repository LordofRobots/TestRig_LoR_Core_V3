# Production Data and Traceability

## Scope

Both production clients maintain an append-only local CSV. The repository deliberately does not implement a central database, Git-based data upload, or multi-station synchronization. Each station owns its own file and manufacturing operations owns export, backup, access control, and retention.

## Storage locations

### Windows

```text
C:\ProgramData\Lord of Robots\LoR Core V3 Test Station\results\lor_core_v3_results.csv
```

The NSIS installer grants standard local users modify access to the application data tree. Application upgrades and uninstall operations preserve ProgramData. The Test History tab reads this file directly and displays at most the newest 2,000 rows; the file itself is not truncated.

Source-development runs write to the ignored repository-level `results` directory.

### Android

The working file is `files/results/lor_core_v3_results.csv` inside the app's private storage. It is accessible through the app, not through ordinary file browsing.

Use **Test History -> Export CSV** and choose a destination in Android's document picker. Normal APK upgrades preserve the private file. Uninstalling the app, clearing app storage, or changing to an APK signed with an incompatible key can destroy access to that history. Export before any such operation.

## Append behavior

- A normal pass or fail appends one row.
- A station error after a production attempt begins appends a failure row when enough context is available.
- Android's flash-only and handshake-only developer diagnostics do not append production rows.
- Existing rows are never edited by the application.
- CSV timestamps use UTC ISO-8601 format.
- `board_id` is the canonical ESP32 factory eFuse MAC; `serial_label` is optional operator-entered text.

## CSV schema

| Field | Meaning |
|---|---|
| `timestamp_utc` | UTC time at the start of the attempt |
| `operator` | Optional operator identifier or initials |
| `serial_label` | Optional printed manufacturing serial/label |
| `board_id` | Canonical eFuse MAC address in normal byte order |
| `com_port` | Windows COM port or Android USB transport label |
| `firmware` | Production firmware version reported by the board |
| `chip` | ESP32 model reported by the board |
| `chip_revision` | ESP32 silicon revision |
| `flash_bytes` | Detected flash capacity in bytes |
| `vin_volts` | Calibrated 20-sample battery voltage average |
| `vin_pass` | Battery result: `true`, `false`, or blank when skipped |
| `wifi_pass` | Wi-Fi scan/RSSI result |
| `wifi_networks` | Count of visible Wi-Fi networks |
| `wifi_target` | Configured target or strongest visible SSID |
| `wifi_rssi_dbm` | RSSI for the evaluated access point |
| `bluetooth_pass` | BLE scan result |
| `btn_a_pass` | Button A transition result |
| `btn_b_pass` | Button B transition result |
| `btn_c_pass` | Button C transition result |
| `btn_d_pass` | Button D transition result |
| `switch_pass` | User-switch transition result |
| `led_pass` | Operator LED-animation approval |
| `overall_pass` | Final result after all required checks |
| `control_mapping` | Mapping/version note used for the controls |
| `details_json` | Complete ordered result list and raw measurements |

## Detailed measurements

`details_json` preserves evidence that does not have a dedicated top-level CSV column. A typical voltage detail contains:

```text
volts=7.869,raw_adc=1129.6,samples=20,min=6.000,max=12.000
```

BLE details include the observed advertisement count and strongest RSSI. Control details identify the expected GPIO and every changed GPIO. Upload/station failures preserve their error message.

When Android's **Check Battery Voltage** setting is off:

- the board is not sent a `VIN` command;
- the live result and `details_json` say the check was skipped;
- `vin_volts` and `vin_pass` remain blank;
- VIN is not included in `overall_pass`.

Blank VIN is therefore different from a failed VIN measurement.

## Backup and retention

A simple local production policy is recommended:

1. Export or copy each station's CSV at the end of every shift or production lot.
2. Name the copy with the station identifier and UTC date, for example `station-android-01_2026-08-01.csv`.
3. Store it in the approved manufacturing backup location.
4. Verify that the exported row count and most recent board match Test History.
5. Never use Git commits or public GitHub issues to archive production records.
6. Do not merge files by editing original station logs. Merge only copied exports and retain each source file.

## Privacy

Production CSV files may contain device identifiers, printed serials, operator identifiers, and factory SSIDs. Treat them as manufacturing records. Sanitize all of those fields before sharing a row, screenshot, or diagnostic outside the authorized production environment.
