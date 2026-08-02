#include <jni.h>
#include <android/log.h>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <deque>
#include <string>
#include <thread>
#include <vector>

extern "C" {
#include "esp_loader.h"
#include "esp_loader_io.h"
}

namespace {
constexpr char TAG[] = "LoREspressifFlasher";
constexpr uint32_t ROM_BAUD = 115200;
constexpr uint32_t FLASH_BAUD = 460800;
constexpr uint32_t FLASH_BLOCK = 4096;

JNIEnv *g_env = nullptr;
jobject g_transport = nullptr;
jobject g_listener = nullptr;
jmethodID g_read = nullptr;
jmethodID g_write = nullptr;
jmethodID g_configure = nullptr;
jmethodID g_set_lines = nullptr;
jmethodID g_drain = nullptr;
jmethodID g_status = nullptr;
jmethodID g_progress = nullptr;
std::chrono::steady_clock::time_point g_deadline;
std::string g_java_error;
std::deque<uint8_t> g_receive_queue;

bool capture_java_exception(const char *operation) {
    if (!g_env->ExceptionCheck()) return false;
    jthrowable exception = g_env->ExceptionOccurred();
    g_env->ExceptionClear();
    jclass throwable = g_env->FindClass("java/lang/Throwable");
    jmethodID get_message = g_env->GetMethodID(throwable, "getMessage", "()Ljava/lang/String;");
    auto message = static_cast<jstring>(g_env->CallObjectMethod(exception, get_message));
    const char *utf = message ? g_env->GetStringUTFChars(message, nullptr) : nullptr;
    g_java_error = std::string(operation) + (utf ? ": " + std::string(utf) : " failed");
    if (utf) g_env->ReleaseStringUTFChars(message, utf);
    if (message) g_env->DeleteLocalRef(message);
    g_env->DeleteLocalRef(throwable);
    g_env->DeleteLocalRef(exception);
    return true;
}

void notify_status(const std::string &value) {
    jstring text = g_env->NewStringUTF(value.c_str());
    g_env->CallVoidMethod(g_listener, g_status, text);
    g_env->DeleteLocalRef(text);
    capture_java_exception("status callback");
}

void notify_progress(int value) {
    g_env->CallVoidMethod(g_listener, g_progress, std::clamp(value, 0, 100));
    capture_java_exception("progress callback");
}

const char *error_name(esp_loader_error_t error) {
    switch (error) {
        case ESP_LOADER_SUCCESS: return "success";
        case ESP_LOADER_ERROR_FAIL: return "unspecified failure";
        case ESP_LOADER_ERROR_TIMEOUT: return "timed out";
        case ESP_LOADER_ERROR_IMAGE_SIZE: return "image exceeds flash size";
        case ESP_LOADER_ERROR_INVALID_MD5: return "flash verification failed";
        case ESP_LOADER_ERROR_INVALID_PARAM: return "invalid flashing parameter";
        case ESP_LOADER_ERROR_INVALID_TARGET: return "invalid ESP target";
        case ESP_LOADER_ERROR_UNSUPPORTED_CHIP: return "unsupported ESP chip";
        case ESP_LOADER_ERROR_UNSUPPORTED_FUNC: return "unsupported loader operation";
        case ESP_LOADER_ERROR_INVALID_RESPONSE: return "invalid loader response";
        default: return "unknown error";
    }
}

std::string loader_failure(const char *operation, esp_loader_error_t error) {
    std::string value = std::string(operation) + ": " + error_name(error);
    if (!g_java_error.empty()) value += " (" + g_java_error + ")";
    return value;
}

bool call_lines(bool dtr, bool rts) {
    g_env->CallVoidMethod(g_transport, g_set_lines, static_cast<jboolean>(dtr), static_cast<jboolean>(rts));
    return !capture_java_exception("USB control-line update");
}

bool call_configure(uint32_t baud) {
    g_env->CallVoidMethod(g_transport, g_configure, static_cast<jint>(baud));
    return !capture_java_exception("USB baud-rate update");
}
}  // namespace

extern "C" esp_loader_error_t loader_port_write(const uint8_t *data, uint16_t size, uint32_t) {
    jbyteArray bytes = g_env->NewByteArray(size);
    if (!bytes) return ESP_LOADER_ERROR_FAIL;
    g_env->SetByteArrayRegion(bytes, 0, size, reinterpret_cast<const jbyte *>(data));
    g_env->CallVoidMethod(g_transport, g_write, bytes);
    g_env->DeleteLocalRef(bytes);
    return capture_java_exception("USB write") ? ESP_LOADER_ERROR_FAIL : ESP_LOADER_SUCCESS;
}

extern "C" esp_loader_error_t loader_port_read(uint8_t *data, uint16_t size, uint32_t timeout) {
    size_t received = 0;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout);
    while (received < size) {
        while (received < size && !g_receive_queue.empty()) {
            data[received++] = g_receive_queue.front();
            g_receive_queue.pop_front();
        }
        if (received == size) break;
        auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - std::chrono::steady_clock::now()).count();
        if (remaining <= 0) return ESP_LOADER_ERROR_TIMEOUT;
        auto part = static_cast<jbyteArray>(g_env->CallObjectMethod(
                g_transport, g_read, 512, static_cast<jint>(std::min<int64_t>(remaining, 100))));
        if (capture_java_exception("USB read")) return ESP_LOADER_ERROR_FAIL;
        if (!part) continue;
        jsize count = g_env->GetArrayLength(part);
        if (count > 0) {
            std::vector<jbyte> packet(count);
            g_env->GetByteArrayRegion(part, 0, count, packet.data());
            for (jbyte value : packet) g_receive_queue.push_back(static_cast<uint8_t>(value));
        }
        g_env->DeleteLocalRef(part);
    }
    return ESP_LOADER_SUCCESS;
}

extern "C" void loader_port_delay_ms(uint32_t ms) {
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

extern "C" void loader_port_start_timer(uint32_t ms) {
    g_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(ms);
}

extern "C" uint32_t loader_port_remaining_time(void) {
    auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(g_deadline - std::chrono::steady_clock::now()).count();
    return remaining > 0 ? static_cast<uint32_t>(remaining) : 0;
}

extern "C" void loader_port_enter_bootloader(void) {
    g_receive_queue.clear();
    g_env->CallVoidMethod(g_transport, g_drain);
    capture_java_exception("USB input drain");
    call_lines(false, false);
    loader_port_delay_ms(50);
    call_lines(false, true);
    loader_port_delay_ms(120);
    call_lines(true, false);
    loader_port_delay_ms(250);
    call_lines(false, false);
    loader_port_delay_ms(100);
}

extern "C" void loader_port_reset_target(void) {
    call_lines(false, true);
    loader_port_delay_ms(100);
    call_lines(false, false);
    loader_port_delay_ms(100);
}

extern "C" esp_loader_error_t loader_port_change_transmission_rate(uint32_t baud) {
    return call_configure(baud) ? ESP_LOADER_SUCCESS : ESP_LOADER_ERROR_FAIL;
}

extern "C" void loader_port_debug_print(const char *text) {
    __android_log_print(ANDROID_LOG_DEBUG, TAG, "%s", text ? text : "");
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_lordofrobots_lorcoretest_Esp32Flasher_nativeFlash(
        JNIEnv *env, jclass, jobject transport, jobjectArray payloads,
        jintArray addresses, jobjectArray names, jobject listener) {
    g_env = env;
    g_transport = transport;
    g_listener = listener;
    g_java_error.clear();

    jclass transport_class = env->GetObjectClass(transport);
    g_read = env->GetMethodID(transport_class, "nativeRead", "(II)[B");
    g_write = env->GetMethodID(transport_class, "write", "([B)V");
    g_configure = env->GetMethodID(transport_class, "configure", "(I)V");
    g_set_lines = env->GetMethodID(transport_class, "setLines", "(ZZ)V");
    g_drain = env->GetMethodID(transport_class, "drain", "()V");
    jclass listener_class = env->GetObjectClass(listener);
    g_status = env->GetMethodID(listener_class, "status", "(Ljava/lang/String;)V");
    g_progress = env->GetMethodID(listener_class, "progress", "(I)V");
    if (capture_java_exception("native bridge setup") || !g_read || !g_write || !g_configure ||
            !g_set_lines || !g_drain || !g_status || !g_progress) {
        return env->NewStringUTF("Unable to initialize the Espressif Android bridge");
    }

    call_configure(ROM_BAUD);
    notify_progress(0);
    notify_status("Entering ESP32 download mode and loading Espressif flasher...");
    esp_loader_connect_args_t connect = ESP_LOADER_CONNECT_DEFAULT();
    connect.sync_timeout = 1000;
    connect.trials = 10;
    esp_loader_error_t result = esp_loader_connect_with_stub(&connect);
    if (result != ESP_LOADER_SUCCESS) {
        std::string error = loader_failure("ESP32 connection failed", result);
        loader_port_reset_target();
        return env->NewStringUTF(error.c_str());
    }

    if (esp_loader_get_target() != ESP32_CHIP) {
        std::string error = "Connected device is not the ESP32 used by LoR Core V3";
        loader_port_reset_target();
        return env->NewStringUTF(error.c_str());
    }

    notify_status("Espressif flasher connected; increasing upload speed...");
    result = esp_loader_change_transmission_rate_stub(ROM_BAUD, FLASH_BAUD);
    if (result == ESP_LOADER_SUCCESS) result = loader_port_change_transmission_rate(FLASH_BAUD);
    if (result != ESP_LOADER_SUCCESS) {
        std::string error = loader_failure("Unable to set production upload speed", result);
        loader_port_reset_target();
        return env->NewStringUTF(error.c_str());
    }

    jsize image_count = env->GetArrayLength(payloads);
    if (image_count <= 0 || env->GetArrayLength(addresses) != image_count || env->GetArrayLength(names) != image_count) {
        loader_port_reset_target();
        return env->NewStringUTF("Firmware package layout is invalid");
    }

    std::vector<jint> offsets(image_count);
    env->GetIntArrayRegion(addresses, 0, image_count, offsets.data());
    uint64_t total = 0;
    for (jsize index = 0; index < image_count; ++index) {
        auto payload = static_cast<jbyteArray>(env->GetObjectArrayElement(payloads, index));
        total += env->GetArrayLength(payload);
        env->DeleteLocalRef(payload);
    }

    uint64_t completed = 0;
    std::vector<uint8_t> block(FLASH_BLOCK, 0xff);
    for (jsize index = 0; index < image_count; ++index) {
        auto payload = static_cast<jbyteArray>(env->GetObjectArrayElement(payloads, index));
        auto name = static_cast<jstring>(env->GetObjectArrayElement(names, index));
        const char *name_utf = env->GetStringUTFChars(name, nullptr);
        jsize length = env->GetArrayLength(payload);
        notify_status(std::string("Erasing and uploading ") + name_utf + "...");
        env->ReleaseStringUTFChars(name, name_utf);

        result = esp_loader_flash_start(static_cast<uint32_t>(offsets[index]), length, FLASH_BLOCK);
        if (result == ESP_LOADER_SUCCESS) {
            for (jsize position = 0; position < length; position += FLASH_BLOCK) {
                jsize count = std::min<jsize>(FLASH_BLOCK, length - position);
                std::fill(block.begin(), block.end(), 0xff);
                env->GetByteArrayRegion(payload, position, count, reinterpret_cast<jbyte *>(block.data()));
                result = esp_loader_flash_write(block.data(), count);
                if (result != ESP_LOADER_SUCCESS) break;
                completed += count;
                notify_progress(static_cast<int>((completed * 95) / total));
            }
        }
        if (result == ESP_LOADER_SUCCESS) {
            notify_status("Verifying uploaded image...");
            result = esp_loader_flash_verify();
        }
        env->DeleteLocalRef(name);
        env->DeleteLocalRef(payload);
        if (result != ESP_LOADER_SUCCESS) {
            std::string error = loader_failure("Firmware upload failed", result);
            loader_port_reset_target();
            return env->NewStringUTF(error.c_str());
        }
    }

    notify_status("Firmware verified; restarting LoR Core V3...");
    notify_progress(100);
    call_configure(ROM_BAUD);
    esp_loader_reset_target();
    return nullptr;
}
