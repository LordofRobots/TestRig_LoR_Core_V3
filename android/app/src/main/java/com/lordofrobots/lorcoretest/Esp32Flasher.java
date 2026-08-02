package com.lordofrobots.lorcoretest;

import java.util.List;

/** Thin Java wrapper around Espressif's ESP Serial Flasher native library. */
final class Esp32Flasher {
    interface Listener {
        void status(String text);
        void progress(int percent);
    }

    static {
        System.loadLibrary("lor_esp_flasher");
    }

    private final UsbTransport serial;
    private final Listener listener;

    Esp32Flasher(UsbTransport serial, Listener listener) {
        this.serial = serial;
        this.listener = listener;
    }

    void flash(List<FirmwareRepository.Image> images) throws Exception {
        byte[][] payloads = new byte[images.size()][];
        int[] addresses = new int[images.size()];
        String[] names = new String[images.size()];
        for (int index = 0; index < images.size(); index++) {
            FirmwareRepository.Image image = images.get(index);
            payloads[index] = image.data;
            addresses[index] = image.address;
            names[index] = image.name;
        }

        String error = nativeFlash(serial, payloads, addresses, names, listener);
        if (error != null) throw new IllegalStateException(error);
    }

    private static native String nativeFlash(
            UsbTransport transport,
            byte[][] payloads,
            int[] addresses,
            String[] names,
            Listener listener);
}
