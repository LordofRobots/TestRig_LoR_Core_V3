cmake_minimum_required(VERSION 3.22.1)
project(lor_esp_flasher LANGUAGES C CXX)

set(SERIAL_FLASHER_INTERFACE_UART true)
set(SERIAL_FLASHER_DEBUG_TRACE false)
set(SERIAL_FLASHER_WRITE_BLOCK_RETRIES 5)
set(MD5_ENABLED true)
set(PORT USER_DEFINED)
add_subdirectory(third_party/esp-serial-flasher-1.11.0 esp_serial_flasher)

add_library(lor_esp_flasher SHARED android_flasher_bridge.cpp)
target_compile_features(lor_esp_flasher PRIVATE cxx_std_17)
target_link_options(lor_esp_flasher PRIVATE "-Wl,-z,max-page-size=16384")
target_link_libraries(lor_esp_flasher PRIVATE flasher log)
