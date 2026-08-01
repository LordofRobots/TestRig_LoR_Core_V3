package com.lordofrobots.lorcoretest;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.List;

final class Esp32Flasher {
    interface Listener { void status(String text); void progress(int percent); }
    private static final int SYNC = 0x08, FLASH_BEGIN = 0x02, FLASH_DATA = 0x03, FLASH_END = 0x04;
    private static final int BLOCK = 0x400;
    private final UsbTransport serial;
    private final Listener listener;

    Esp32Flasher(UsbTransport serial, Listener listener) { this.serial = serial; this.listener = listener; }

    void flash(List<FirmwareRepository.Image> images) throws Exception {
        listener.status("Entering ESP32 download mode...");
        enterBootloader();
        boolean synced = false;
        for (int attempt = 0; attempt < 7 && !synced; attempt++) {
            try { command(SYNC, syncPayload(), 0, 1500); synced = true; }
            catch (Exception ignored) { Thread.sleep(100); }
        }
        if (!synced) throw new IllegalStateException("ESP32 bootloader did not respond. Check USB-C and automatic BOOT/RESET wiring.");

        long total = 0, complete = 0;
        for (FirmwareRepository.Image image : images) total += image.data.length;
        for (FirmwareRepository.Image image : images) {
            listener.status("Uploading " + image.name + "...");
            int blocks = (image.data.length + BLOCK - 1) / BLOCK;
            command(FLASH_BEGIN, words(image.data.length, blocks, BLOCK, image.address), 0, 20000);
            for (int sequence = 0; sequence < blocks; sequence++) {
                int offset = sequence * BLOCK;
                int count = Math.min(BLOCK, image.data.length - offset);
                byte[] block = new byte[BLOCK];
                java.util.Arrays.fill(block, (byte) 0xff);
                System.arraycopy(image.data, offset, block, 0, count);
                ByteArrayOutputStream payload = new ByteArrayOutputStream(BLOCK + 16);
                payload.write(words(BLOCK, sequence, 0, 0));
                payload.write(block);
                command(FLASH_DATA, payload.toByteArray(), checksum(block), 5000);
                complete += count;
                listener.progress((int) Math.min(99, complete * 100 / total));
            }
        }
        listener.status("Finalizing firmware...");
        command(FLASH_END, words(0), 0, 5000);
        listener.progress(100);
        Thread.sleep(250);
        hardReset();
    }

    private void enterBootloader() throws Exception {
        serial.setLines(false, true); Thread.sleep(100);
        serial.setLines(true, false); Thread.sleep(100);
        serial.setLines(false, false); Thread.sleep(50);
        serial.drain();
    }

    private void hardReset() throws Exception {
        serial.setLines(false, true); Thread.sleep(100);
        serial.setLines(false, false); Thread.sleep(100);
    }

    private byte[] syncPayload() {
        byte[] payload = new byte[36];
        payload[0] = 0x07; payload[1] = 0x07; payload[2] = 0x12; payload[3] = 0x20;
        java.util.Arrays.fill(payload, 4, payload.length, (byte) 0x55);
        return payload;
    }

    private void command(int opcode, byte[] payload, int checksum, int timeoutMs) throws Exception {
        ByteBuffer packet = ByteBuffer.allocate(8 + payload.length).order(ByteOrder.LITTLE_ENDIAN);
        packet.put((byte) 0x00).put((byte) opcode).putShort((short) payload.length).putInt(checksum).put(payload);
        serial.write(slip(packet.array()));
        long deadline = System.currentTimeMillis() + timeoutMs;
        while (System.currentTimeMillis() < deadline) {
            byte[] response = readFrame((int) Math.max(50, deadline - System.currentTimeMillis()));
            if (response.length < 8 || (response[1] & 0xff) != opcode) continue;
            int length = (response[2] & 0xff) | ((response[3] & 0xff) << 8);
            if (response.length < 8 + length) continue;
            if (length >= 2) {
                int status = response[8 + length - (length >= 4 ? 4 : 2)] & 0xff;
                if (status != 0) throw new IllegalStateException(String.format("ESP32 loader command 0x%02X failed (status %d)", opcode, status));
            }
            return;
        }
        throw new java.util.concurrent.TimeoutException(String.format("ESP32 loader command 0x%02X timed out", opcode));
    }

    private byte[] readFrame(int timeoutMs) throws Exception {
        long deadline = System.currentTimeMillis() + timeoutMs;
        ByteArrayOutputStream frame = new ByteArrayOutputStream();
        boolean started = false, escaped = false;
        while (System.currentTimeMillis() < deadline) {
            byte[] part = serial.readSome(512, (int) Math.min(100, Math.max(1, deadline - System.currentTimeMillis())));
            for (byte raw : part) {
                int value = raw & 0xff;
                if (!started) { if (value == 0xc0) started = true; continue; }
                if (value == 0xc0) { if (frame.size() > 0) return frame.toByteArray(); else continue; }
                if (escaped) {
                    if (value == 0xdc) frame.write(0xc0); else if (value == 0xdd) frame.write(0xdb); else { frame.write(0xdb); frame.write(value); }
                    escaped = false;
                } else if (value == 0xdb) escaped = true; else frame.write(value);
            }
        }
        throw new java.util.concurrent.TimeoutException("Timed out waiting for ESP32 loader packet");
    }

    private static byte[] slip(byte[] data) {
        ByteArrayOutputStream output = new ByteArrayOutputStream(data.length + 16);
        output.write(0xc0);
        for (byte raw : data) {
            int value = raw & 0xff;
            if (value == 0xc0) { output.write(0xdb); output.write(0xdc); }
            else if (value == 0xdb) { output.write(0xdb); output.write(0xdd); }
            else output.write(value);
        }
        output.write(0xc0);
        return output.toByteArray();
    }

    private static int checksum(byte[] data) { int value = 0xef; for (byte item : data) value ^= item & 0xff; return value; }
    private static byte[] words(int... values) { ByteBuffer b = ByteBuffer.allocate(values.length * 4).order(ByteOrder.LITTLE_ENDIAN); for (int value : values) b.putInt(value); return b.array(); }
}
