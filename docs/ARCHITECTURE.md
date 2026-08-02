# System Architecture

## Design objective

The LoR Core V3 Production Test System separates platform-specific operator interfaces from one board protocol and one approved firmware implementation. Windows and Android can be deployed independently, but a board receives equivalent test logic and fail-safe behavior from either station.

## Components

| Component | Responsibility |
|---|---|
| Windows station | COM detection, verified upload, guided workflow, history, CSV, and automatic updates |
| Android station | USB Host/CH340 transport, native upload, guided workflow, history, and CSV export |
| Production firmware | Hardware measurements, RF scans, controls, LEDs, identity, and persistent state |
| Firmware manifest/package | Product/protocol identity, exact flash layout, and SHA-256 trust metadata |
| Windows installer | Machine-wide frozen runtime, shortcuts, permissions, and preserved ProgramData |
| GitHub Release | Public Windows installer, common firmware ZIP, and update manifest |
| Local CSV | Append-only manufacturing traceability owned by each station |

## Runtime topology

```text
                         Public GitHub Release
                       /                       \
        runtime update/                         \build-time sync
                     v                           v
          Windows production app          Android production APK
                    \                         /
                     \ USB serial / CH340   /
                      v                     v
                         LoR Core V3 ESP32
                                  |
                  production-test firmware / NVS
```

Windows can use bundled or newer cached firmware at runtime. Android validates and embeds the common package when the APK is built. Neither platform depends on the other at runtime, and neither needs the network to test a board.

## Production transaction

```text
Board attached
    -> transport selected and opened
    -> ESP32 ROM bootloader entered
    -> four approved images programmed
    -> target reset
    -> startup animation completes
    -> INFO identity/protocol handshake
    -> TEST_START stores provisional failure
    -> VIN (when required)
    -> Wi-Fi
    -> BLE
    -> LED operator confirmation
    -> buttons A-D and switch
    -> TEST_PASS or TEST_FAIL
    -> local CSV append
    -> Test History refresh
```

Upload/handshake diagnostics used during development stop before `TEST_START` and do not create production records or alter the board's pass/fail latch.

## Fail-safe state machine

```text
Power on
   |
   v
Rainbow startup
   |
   +-- NVS failed = true  --> locked red
   |
   +-- NVS failed = false --> icy-blue idle

TEST_START --> write failed=true
   |
   +-- any failure/interruption --> remains failed=true
   |
   +-- all required checks pass --> TEST_PASS --> write failed=false
```

Only a complete pass clears failure. This makes power loss and station failure conservative.

## Firmware execution model

The board does not autonomously run measurements at power-up. Idle firmware work is limited to:

- reading persistent NVS state;
- playing the startup presentation;
- rendering icy-blue idle or locked red;
- showing button color feedback when not red-latched;
- polling USB serial for commands.

VIN, Wi-Fi, BLE, LED demo, and production input snapshots occur only in response to host commands. This prevents RF scans and ADC work from disrupting the baseline LED animation.

## Hardware abstraction boundary

The firmware owns LoR-specific pins and measurements. The clients own transport, workflow, configuration, user prompts, and audit data.

| Firmware-owned | Client-owned |
|---|---|
| GPIO mapping | Board detection and USB permission |
| ADC sampling/calibration | Firmware package selection/validation |
| Wi-Fi/BLE scan implementation | Thresholds and required/optional checks |
| LED presentation and persistent red | Operator prompts and confirmation |
| NVS pass/fail state | CSV append and history display |

## Package trust boundary

An approved manifest must match:

- schema 1;
- product `LoR Core V3`;
- serial protocol 1;
- a `production-test-x.y` firmware version;
- exactly four safe filenames;
- addresses `0x1000`, `0x8000`, `0xe000`, and `0x10000`;
- package and per-image SHA-256 values.

Windows also validates the application installer hash from the update manifest. Validation failure never replaces the current verified artifact.

## Platform-specific transport

### Windows

The UI discovers serial ports and invokes the bundled standalone esptool at 921600 baud for programming. It then opens the board protocol at 115200 baud through pyserial.

### Android

The app uses Android USB Host APIs and `usb-serial-for-android` for CH340 access. Native Espressif ESP Serial Flasher code enters the ROM bootloader, uploads the stub, writes each image, verifies MD5, and resets the target. The Java protocol session then operates at 115200 baud.

## Data architecture

There is no central service. Each platform appends the same ordered CSV schema locally. `details_json` retains raw/structured evidence not represented by dedicated columns. See [Data and Traceability](DATA_AND_TRACEABILITY.md).

## Installed data locations

| Data | Windows | Android |
|---|---|---|
| Application | Program Files | APK-managed app directory |
| Results | ProgramData CSV | Private app storage |
| Firmware | Bundled plus verified ProgramData cache | Verified APK assets |
| Updates | Verified ProgramData downloads | Manual APK installation |

## Resource and lifecycle design

Windows reuses a single animated-image buffer, pauses animation while minimized, lazy-loads history, and caps displayed rows at 2,000. Android uses one activity, one single-thread production executor, bounded result/history views, and closes the USB transport in every completion path. App destruction unregisters the USB receiver and stops the worker.

## Version compatibility

Protocol version is the host/firmware compatibility boundary. A client rejects a wrong product or unsupported manifest protocol. Firmware version and app version evolve independently as documented in [Release Process](RELEASE_PROCESS.md).
