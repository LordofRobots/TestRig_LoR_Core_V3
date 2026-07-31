// LoR Core V3 focused production-test firmware
// Target: ESP32 Dev Module using Espressif Arduino core 3.x

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <FastLED.h>
#include <Preferences.h>
#include <WiFi.h>

namespace LorV3 {

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint8_t LED_PIN = 33;
constexpr uint8_t LED_COUNT = 4;
constexpr uint8_t VIN_SENSE = 34;
constexpr uint8_t INPUT_PINS[] = {35, 36, 37, 38, 39};
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
  Serial.print(F("{\"type\":\"info\",\"product\":\"LoR Core V3\",\"firmware\":\"production-test-1.8\",\"chip\":"));
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

void playRainbowWash() {
  breathing = false;
  const uint32_t started = millis();
  while (millis() - started < 1000) {
    const uint8_t hue = uint8_t((millis() - started) / 4);
    fill_rainbow(leds, LED_COUNT, hue, 40);
    FastLED.show();
    delay(15);
  }
  FastLED.clear(true);
}

void startLedDemo() {
  if (!testActive) {
    result("LED_DEMO", false, "TEST_START is required before LED_DEMO");
    return;
  }
  playRainbowWash();
  breathing = true;
  result("LED_DEMO", true, "one-second rainbow complete; icy-blue breathing active");
}

void showLockedFailure() {
  breathing = false;
  fill_solid(leds, LED_COUNT, CRGB(255, 0, 0));
  FastLED.show();
}

void startProductionTest() {
  // Fail-safe: a reset or power loss during a test must reboot to locked red.
  preferences.putBool("failed", true);
  failureLocked = false;
  testActive = true;
  breathing = true;
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
    breathing = true;
    result("TEST_PASS", true, "solid green shown for two seconds; baseline animation restored");
  } else {
    preferences.putBool("failed", true);
    failureLocked = true;
    showLockedFailure();
    result("TEST_FAIL", true, "failure latched; LEDs remain red across power cycles");
  }
}

void updateBreathingLeds() {
  if (failureLocked || !breathing || millis() - lastLedFrameMs < 16) return;
  lastLedFrameMs = millis();
  const uint32_t now = millis();
  // An asymmetric 270-degree envelope creates a bright comet head followed
  // by a long fading tail. The remaining quarter of the ring stays dark.
  const uint8_t rotationPhase = uint8_t(now / 12);
  const uint8_t breath = scale8(sin8(uint8_t(now / 20)), 75) + 180;
  constexpr uint8_t HEAD_LENGTH = 36;
  constexpr uint8_t COMET_LENGTH = 192;

  fill_solid(leds, LED_COUNT, CRGB::Black);
  for (uint8_t led = 0; led < LED_COUNT; ++led) {
    const uint8_t ledPhase = led * (256 / LED_COUNT);
    const uint8_t positionInComet = rotationPhase - ledPhase;
    if (positionInComet >= COMET_LENGTH) continue;

    uint8_t cometLevel;
    if (positionInComet < HEAD_LENGTH) {
      const uint8_t headProgress = uint8_t((uint16_t(positionInComet) * 255) / HEAD_LENGTH);
      cometLevel = ease8InOutQuad(headProgress);
    } else {
      const uint8_t tailProgress = uint8_t(
          (uint16_t(positionInComet - HEAD_LENGTH) * 255) /
          (COMET_LENGTH - HEAD_LENGTH));
      cometLevel = 255 - ease8InOutQuad(tailProgress);
    }

    const uint8_t level = scale8(cometLevel, breath);
    const CRGB cometColor = blend(CRGB(8, 75, 255), CRGB(155, 235, 255), cometLevel);
    leds[led] = cometColor;
    leds[led].nscale8_video(level);
  }
  FastLED.show();
}

bool updateButtonLedOverride() {
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
  playRainbowWash();
  failureLocked = preferences.getBool("failed", false);
  if (failureLocked) {
    showLockedFailure();
  } else {
    breathing = true;
    updateBreathingLeds();
  }
  delay(600);
  Serial.println(F("{\"type\":\"ready\",\"product\":\"LoR Core V3\",\"protocol\":1}"));
  printInfo();
}

void loop() {
  if (Serial.available()) LorV3::handleCommand(Serial.readStringUntil('\n'));
  if (!LorV3::updateButtonLedOverride()) LorV3::updateBreathingLeds();
  delay(2);
}
