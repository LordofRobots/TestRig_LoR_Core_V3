package com.lordofrobots.lorcoretest;

import android.hardware.usb.UsbDeviceConnection;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import java.io.ByteArrayOutputStream;

final class UsbTransport implements AutoCloseable {
    private final UsbDeviceConnection connection;
    private final UsbSerialPort port;

    UsbTransport(UsbDeviceConnection connection, UsbSerialPort port) throws Exception {
        this.connection = connection;
        this.port = port;
        port.open(connection);
        configure(115200);
    }

    synchronized void configure(int baud) throws Exception {
        port.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
    }

    synchronized void write(byte[] data) throws Exception { port.write(data, 5000); }

    synchronized byte[] readSome(int maximum, int timeoutMs) throws Exception {
        byte[] buffer = new byte[maximum];
        int count = port.read(buffer, timeoutMs);
        if (count <= 0) return new byte[0];
        return java.util.Arrays.copyOf(buffer, count);
    }

    synchronized void drain() {
        try { while (port.read(new byte[1024], 20) > 0) { } } catch (Exception ignored) { }
    }

    synchronized void setLines(boolean dtr, boolean rts) throws Exception {
        port.setDTR(dtr);
        port.setRTS(rts);
    }

    String readLine(long timeoutMs) throws Exception {
        long deadline = System.currentTimeMillis() + timeoutMs;
        ByteArrayOutputStream line = new ByteArrayOutputStream();
        while (System.currentTimeMillis() < deadline) {
            byte[] part = readSome(256, 120);
            for (byte value : part) {
                if (value == '\n') return line.toString(java.nio.charset.StandardCharsets.UTF_8.name()).trim();
                if (value != '\r' && line.size() < 8192) line.write(value);
            }
        }
        throw new java.util.concurrent.TimeoutException("Timed out waiting for board response");
    }

    @Override public synchronized void close() {
        try { port.close(); } catch (Exception ignored) { }
        connection.close();
    }
}
