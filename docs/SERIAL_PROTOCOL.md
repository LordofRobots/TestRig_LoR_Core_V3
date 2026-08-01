# LoR Core V3 Production-Test Serial Protocol

The desktop station communicates with the dedicated test firmware over USB serial at 115200 baud. Commands are UTF-8/ASCII lines terminated with `\n`. Responses are one-line JSON objects.

The documented firmware release is `production-test-1.14` and the serial protocol version is `1`.

## Startup messages

At power-up, the firmware reads only the persistent failure flag from NVS. It then plays the 2.3-second spatial rainbow startup, returns the LEDs to black, and fades seamlessly into either the icy-blue spatial orb or the locked-red failure state. After that presentation sequence, the firmware emits:

```json
{"type":"ready","product":"LoR Core V3","protocol":1}
```

It then emits an `info` object containing the firmware version, ESP32 model and revision, flash size, and canonical factory eFuse MAC address. These startup messages report metadata; they do not run a production check.

## Firmware execution model

The firmware does not automatically run voltage, Wi-Fi, Bluetooth, or control tests during startup or idle operation. Those checks execute only in response to the corresponding UI command.

Idle processing is limited to:

- rendering the normal icy-blue spatial orb at approximately 60 frames per second;
- polling buttons A-D so their primary-color LED feedback remains available whenever the normal animation is active;
- waiting for serial commands from the test station.

Wi-Fi scanning occurs only for `WIFI`, BLE scanning only for `BT`, the 20-sample ADC measurement only for `VIN`, and a control snapshot only for `INPUTS`.

## Commands

| Command | Purpose |
|---|---|
| `INFO` | Read board identity and firmware metadata |
| `TEST_START` | Start a test and provisionally latch failure in NVS |
| `VIN <min> <max>` | Average 20 raw ADC readings, calculate voltage, and test the supplied range |
| `WIFI [ssid] <min_rssi>` | Scan Wi-Fi and enforce the target/best-network RSSI floor |
| `BT` | Perform an active three-second BLE scan |
| `LED_DEMO` | Run the dark-to-dark spatial rainbow startup and fade back into the icy-blue orb |
| `INPUTS` | Read GPIO35, GPIO36, GPIO37, GPIO38, and GPIO39 |
| `TEST_PASS` | Clear the failure latch, show green for two seconds, and resume baseline animation |
| `TEST_FAIL` | Persistently latch failure and show solid red |
| `LED_OFF` | Turn LEDs off unless failure is latched |
| `REBOOT` | Restart the ESP32 |

## Result response

Individual checks return:

```json
{"type":"result","test":"VIN","pass":true,"details":"volts=7.869,raw_adc=1129.6,samples=20,min=6.000,max=12.000"}
```

The `details` field is a compact comma-separated set of measurements. The UI stores the complete result list as JSON inside each CSV audit record.

## Fail-safe state

`TEST_START` writes a failed state before testing begins. Only `TEST_PASS` clears it. A reset, power interruption, station crash, or failed check therefore leaves the board visibly red after its next startup rainbow sequence. A failed board still plays the startup presentation first, fades into solid red, and then ignores button color overrides.
