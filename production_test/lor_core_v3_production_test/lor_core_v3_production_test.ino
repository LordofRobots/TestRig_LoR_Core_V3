// LoR Core V3 focused production-test firmware
// Target: ESP32 Dev Module using Espressif Arduino core 3.x

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <FastLED.h>
#include <Preferences.h>
#include <WiFi.h>
#include <math.h>

namespace LorV3 {

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint8_t LED_PIN = 33;
constexpr uint8_t LED_COUNT = 4;
constexpr uint8_t VIN_SENSE = 34;
constexpr uint8_t INPUT_PINS[] = {35, 36, 37, 38, 39};
constexpr float LED_X_MM[] = {0.0f, 0.0f, 46.0f, 46.0f};
constexpr float LED_Y_MM[] = {0.0f, 46.0f, 46.0f, 0.0f};
constexpr float LED_FIELD_CENTER_MM = 23.0f;
constexpr float PI_F = 3.14159265359f;
constexpr float TWO_PI_F = 6.28318530718f;
constexpr float VIN_SLOPE = 0.0063492f;
// Calibrated at an 8.000 V reference on the production fixture. The previous
// 1.079 V offset reported 8.382 V, so the observed +0.382 V error is removed.
constexpr float VIN_OFFSET = 0.697f;

CRGB leds[LED_COUNT];
Preferences preferences;
bool breathing = false;
bool failureLocked = false;
bool testActive = false;
int8_t activeButtonColor = -1;
uint32_t lastLedFrameMs = 0;
uint32_t orbEpochMs = 0;

void jsonString(const String &value) {
  Serial.print('"');
  for (size_t i = 0; i < value.length(); ++i) {
    const char c = value[i];
    if (c == '"' || c == '\\') Serial.print('\\');
    if (c >= 0x20) Serial.print(c);
  }
  Serial.print('"');
}

void result(const char *test, bool pass, const String &details) {
  Serial.print(F("{\"type\":\"result\",\"test\":"));
  jsonString(test);
  Serial.print(F(",\"pass\":"));
  Serial.print(pass ? F("true") : F("false"));
  Serial.print(F(",\"details\":"));
  jsonString(details);
  Serial.println('}');
}

void printInfo() {
  const uint64_t mac = ESP.getEfuseMac();
  char macText[18];
  snprintf(macText, sizeof(macText), "%02X:%02X:%02X:%02X:%02X:%02X",
           uint8_t(mac), uint8_t(mac >> 8), uint8_t(mac >> 16),
           uint8_t(mac >> 24), uint8_t(mac >> 32), uint8_t(mac >> 40));
  Serial.print(F("{\"type\":\"info\",\"product\":\"LoR Core V3\",\"firmware\":\"production-test-1.14\",\"chip\":"));
  jsonString(ESP.getChipModel());
  Serial.print(F(",\"revision\":"));
  Serial.print(ESP.getChipRevision());
  Serial.print(F(",\"flash_bytes\":"));
  Serial.print(ESP.getFlashChipSize());
  Serial.print(F(",\"mac\":\""));
  Serial.print(macText);
  Serial.println(F("\"}"));
}

float readVin(float &averageAdc) {
  uint32_t total = 0;
  analogReadResolution(12);
  constexpr uint8_t SAMPLE_COUNT = 20;
  for (uint8_t i = 0; i < SAMPLE_COUNT; ++i) {
    total += analogRead(VIN_SENSE);
    delay(2);
  }
  averageAdc = total / float(SAMPLE_COUNT);
  return (averageAdc * VIN_SLOPE) + VIN_OFFSET;
}

void testVin(float minimum, float maximum) {
  float averageAdc = 0.0f;
  const float voltage = readVin(averageAdc);
  const bool pass = voltage >= minimum && voltage <= maximum;
  result("VIN", pass,
         String("volts=") + String(voltage, 3) +
             ",raw_adc=" + String(averageAdc, 1) +
             ",samples=20,min=" + String(minimum, 3) +
             ",max=" + String(maximum, 3));
}

void printInputs() {
  Serial.print(F("{\"type\":\"inputs\""));
  for (uint8_t pin : INPUT_PINS) {
    Serial.print(F(",\"gpio"));
    Serial.print(pin);
    Serial.print(F("\":"));
    Serial.print(digitalRead(pin));
  }
  Serial.println('}');
}

void testWifi(const String &expectedSsid, int32_t minimumRssi) {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true, true);
  delay(150);
  const int count = WiFi.scanNetworks(false, true);
  bool found = false;
  int32_t bestRssi = -127;
  int32_t expectedRssi = -127;
  String bestSsid;
  for (int i = 0; i < count; ++i) {
    const int32_t rssi = WiFi.RSSI(i);
    if (rssi > bestRssi) {
      bestRssi = rssi;
      bestSsid = WiFi.SSID(i);
    }
    if (expectedSsid.length() && WiFi.SSID(i) == expectedSsid && rssi > expectedRssi) {
      expectedRssi = rssi;
    }
  }
  if (expectedSsid.length()) {
    found = expectedRssi >= minimumRssi;
  } else {
    found = count > 0 && bestRssi >= minimumRssi;
  }
  const int32_t reportedRssi = expectedSsid.length() ? expectedRssi : bestRssi;
  WiFi.scanDelete();
  WiFi.mode(WIFI_OFF);
  result("WIFI", found,
         String("networks=") + count + ",rssi_dbm=" + reportedRssi +
             ",min_rssi_dbm=" + minimumRssi + ",target=" +
             (expectedSsid.length() ? expectedSsid : bestSsid));
}

void testBluetooth() {
  if (!BLEDevice::init("LoR-Core-V3-Test")) {
    result("BLUETOOTH", false, "BLE stack failed to initialize");
    return;
  }

  BLEScan *scanner = BLEDevice::getScan();
  scanner->setActiveScan(true);
  scanner->setInterval(100);
  scanner->setWindow(80);
  BLEScanResults *scanResults = scanner->start(3, false);

  int count = scanResults == nullptr ? 0 : scanResults->getCount();
  int bestRssi = -127;
  String bestName;
  for (int index = 0; scanResults != nullptr && index < count; ++index) {
    BLEAdvertisedDevice device = scanResults->getDevice(index);
    if (device.getRSSI() > bestRssi) {
      bestRssi = device.getRSSI();
      bestName = device.haveName() ? device.getName() : String("unnamed");
    }
  }

  scanner->clearResults();
  BLEDevice::deinit(false);
  const bool pass = scanResults != nullptr && count > 0;
  result("BLUETOOTH", pass,
         String("devices=") + count + ",best_rssi_dbm=" + bestRssi + ",best_device=" + bestName);
}

float smoothStep(float value) {
  value = constrain(value, 0.0f, 1.0f);
  return value * value * (3.0f - (2.0f * value));
}

void renderSpatialOrb(uint32_t now, CRGB output[]) {
  const uint32_t elapsed = now - orbEpochMs;
  const float orbitPhase = (elapsed % 3600) * (TWO_PI_F / 3600.0f);
  const float breathPhase = (elapsed % 5200) * (TWO_PI_F / 5200.0f);
  const float centerX = LED_FIELD_CENTER_MM + (cosf(orbitPhase) * 16.5f);
  const float centerY = LED_FIELD_CENTER_MM + (sinf(orbitPhase) * 16.5f);
  const float breath = 0.78f + (0.22f * ((sinf(breathPhase) + 1.0f) * 0.5f));

  for (uint8_t led = 0; led < LED_COUNT; ++led) {
    const float dx = LED_X_MM[led] - centerX;
    const float dy = LED_Y_MM[led] - centerY;
    const float distance = sqrtf((dx * dx) + (dy * dy));
    const float glow = smoothStep(1.0f - (distance / 49.0f));
    if (glow <= 0.002f) {
      output[led] = CRGB::Black;
      continue;
    }
    const uint8_t colorMix = uint8_t(glow * 255.0f);
    const uint8_t level = uint8_t(glow * breath * 255.0f);
    output[led] = blend(CRGB(5, 65, 235), CRGB(175, 240, 255), colorMix);
    output[led].nscale8_video(level);
  }
}

void playSpatialRainbowStartup() {
  breathing = false;
  const uint32_t started = millis();
  constexpr uint32_t DURATION_MS = 2300;
  // Begin at LED 1 (top-left), rotate 1.5 times, and finish at LED 3
  // (bottom-right). The global envelope guarantees black at both ends.
  constexpr float START_ANGLE = -2.35619449f;
  constexpr float ROTATIONS = 1.5f;

  while (millis() - started < DURATION_MS) {
    const uint32_t elapsed = millis() - started;
    const float progress = constrain(elapsed / float(DURATION_MS), 0.0f, 1.0f);
    // Keep rotating at a constant rate until the light is fully gone. Easing
    // position here makes the vortex appear to stop before it reaches black.
    const float travel = progress;
    const float pulse = sinf(PI_F * progress);
    const float envelope = pulse * pulse;
    const float bloom = envelope * envelope;
    const float focusAngle = START_ANGLE + (travel * TWO_PI_F * ROTATIONS);

    for (uint8_t led = 0; led < LED_COUNT; ++led) {
      const float dx = LED_X_MM[led] - LED_FIELD_CENTER_MM;
      const float dy = LED_Y_MM[led] - LED_FIELD_CENTER_MM;
      const float ledAngle = atan2f(dy, dx);

      // A continuously rotating focal glow provides motion. At the midpoint,
      // bloom raises every corner so the complete rainbow wheel is visible.
      const float directional = 0.5f + (0.5f * cosf(ledAngle - focusAngle));
      const float focus = directional * directional * directional;
      const float ambient = 0.07f + (0.55f * bloom);
      const float intensity = envelope * (ambient + ((1.0f - ambient) * focus));

      float angularHue = (ledAngle + PI_F) / TWO_PI_F;
      if (angularHue < 0.0f) angularHue += 1.0f;
      const uint8_t hue = uint8_t((angularHue * 255.0f) + (travel * 300.0f));
      leds[led] = CHSV(hue, 245, uint8_t(intensity * 255.0f));
    }
    FastLED.show();
    delay(16);
  }
  fill_solid(leds, LED_COUNT, CRGB::Black);
  FastLED.show();
}

void transitionFromCurrent(bool toFailure) {
  CRGB startingColors[LED_COUNT];
  CRGB targetColors[LED_COUNT];
  for (uint8_t led = 0; led < LED_COUNT; ++led) startingColors[led] = leds[led];

  breathing = false;
  constexpr uint32_t DURATION_MS = 700;
  const uint32_t started = millis();
  if (!toFailure) orbEpochMs = started;
  while (millis() - started < DURATION_MS) {
    const uint32_t now = millis();
    const float progress = constrain(
        (now - started) / float(DURATION_MS), 0.0f, 1.0f);
    // A linear entrance starts changing on the first frame without the initial
    // pause of smoothstep or the brightness jump of an ease-out curve.
    const float easedProgress = toFailure
                                    ? smoothStep(progress)
                                    : progress;
    const uint8_t mixAmount = uint8_t(easedProgress * 255.0f);
    if (toFailure) {
      fill_solid(targetColors, LED_COUNT, CRGB(255, 0, 0));
    } else {
      renderSpatialOrb(now, targetColors);
    }
    for (uint8_t led = 0; led < LED_COUNT; ++led) {
      leds[led] = blend(startingColors[led], targetColors[led], mixAmount);
    }
    FastLED.show();
    delay(16);
  }

  failureLocked = toFailure;
  breathing = !toFailure;
  if (toFailure) {
    fill_solid(leds, LED_COUNT, CRGB(255, 0, 0));
  } else {
    renderSpatialOrb(millis(), leds);
  }
  FastLED.show();
}

void startLedDemo() {
  if (!testActive) {
    result("LED_DEMO", false, "TEST_START is required before LED_DEMO");
    return;
  }
  playSpatialRainbowStartup();
  transitionFromCurrent(false);
  result("LED_DEMO", true, "spatial rainbow startup complete; icy-blue orb active");
}

void showLockedFailure() {
  breathing = false;
  fill_solid(leds, LED_COUNT, CRGB(255, 0, 0));
  FastLED.show();
}

void startProductionTest() {
  // Fail-safe: a reset or power loss during a test must reboot to locked red.
  preferences.putBool("failed", true);
  testActive = true;
  transitionFromCurrent(false);
  result("TEST_START", true, "failure state pre-latched until a complete pass");
}

void finishProductionTest(bool passed) {
  testActive = false;
  if (passed) {
    preferences.putBool("failed", false);
    failureLocked = false;
    breathing = false;
    fill_solid(leds, LED_COUNT, CRGB(0, 255, 0));
    FastLED.show();
    delay(2000);
    transitionFromCurrent(false);
    result("TEST_PASS", true, "solid green shown for two seconds; spatial orb restored");
  } else {
    preferences.putBool("failed", true);
    transitionFromCurrent(true);
    result("TEST_FAIL", true, "failure latched; LEDs remain red across power cycles");
  }
}

void updateBreathingLeds() {
  if (failureLocked || !breathing || millis() - lastLedFrameMs < 16) return;
  lastLedFrameMs = millis();
  renderSpatialOrb(millis(), leds);
  FastLED.show();
}

bool updateButtonLedOverride() {
  // Button color feedback is always available during the normal animation.
  if (failureLocked || !breathing) return false;

  int8_t pressed = -1;
  if (digitalRead(35) == LOW) pressed = 0;       // A - yellow
  else if (digitalRead(39) == LOW) pressed = 1;  // B - green
  else if (digitalRead(38) == LOW) pressed = 2;  // C - red
  else if (digitalRead(37) == LOW) pressed = 3;  // D - blue

  if (pressed >= 0) {
    if (pressed != activeButtonColor) {
      const CRGB colors[] = {
          CRGB(255, 210, 0), CRGB(0, 255, 0), CRGB(255, 0, 0), CRGB(0, 80, 255)};
      fill_solid(leds, LED_COUNT, colors[pressed]);
      FastLED.show();
      activeButtonColor = pressed;
    }
    return true;
  }

  if (activeButtonColor >= 0) {
    activeButtonColor = -1;
    lastLedFrameMs = 0;
  }
  return false;
}

void handleCommand(String line) {
  line.trim();
  if (!line.length()) return;
  String command = line;
  const int firstSpace = line.indexOf(' ');
  if (firstSpace >= 0) command = line.substring(0, firstSpace);
  command.toUpperCase();

  if (command == "INFO") {
    printInfo();
  } else if (command == "TEST_START") {
    startProductionTest();
  } else if (command == "TEST_PASS") {
    finishProductionTest(true);
  } else if (command == "TEST_FAIL") {
    finishProductionTest(false);
  } else if (command == "INPUTS") {
    printInputs();
  } else if (command == "VIN") {
    float minimum = 4.0f, maximum = 15.0f;
    sscanf(line.c_str(), "%*s %f %f", &minimum, &maximum);
    testVin(minimum, maximum);
  } else if (command == "WIFI") {
    int minimumRssi = -85;
    String ssid;
    if (firstSpace >= 0) {
      const String args = line.substring(firstSpace + 1);
      const int finalSpace = args.lastIndexOf(' ');
      if (finalSpace >= 0) {
        ssid = args.substring(0, finalSpace);
        minimumRssi = args.substring(finalSpace + 1).toInt();
      } else {
        minimumRssi = args.toInt();
      }
      ssid.trim();
    }
    testWifi(ssid, minimumRssi);
  } else if (command == "BT") {
    testBluetooth();
  } else if (command == "LED_DEMO") {
    startLedDemo();
  } else if (command == "LED_OFF") {
    if (failureLocked) {
      result("LED_OFF", false, "failure indication is locked");
    } else {
      breathing = false;
      FastLED.clear(true);
      result("LED_OFF", true, "LEDs off");
    }
  } else if (command == "REBOOT") {
    result("REBOOT", true, "restarting");
    Serial.flush();
    ESP.restart();
  } else {
    result("COMMAND", false, String("unknown command: ") + line);
  }
}

}  // namespace LorV3

void setup() {
  using namespace LorV3;
  Serial.begin(SERIAL_BAUD);
  Serial.setTimeout(100);
  for (uint8_t pin : INPUT_PINS) pinMode(pin, INPUT);
  pinMode(VIN_SENSE, INPUT);
  FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, LED_COUNT);
  FastLED.setBrightness(255);
  preferences.begin("lor-test", false);
  failureLocked = preferences.getBool("failed", false);
  playSpatialRainbowStartup();
  transitionFromCurrent(failureLocked);
  Serial.println(F("{\"type\":\"ready\",\"product\":\"LoR Core V3\",\"protocol\":1}"));
  printInfo();
}

void loop() {
  if (Serial.available()) LorV3::handleCommand(Serial.readStringUntil('\n'));
  if (!LorV3::updateButtonLedOverride()) LorV3::updateBreathingLeds();
  delay(2);
}
