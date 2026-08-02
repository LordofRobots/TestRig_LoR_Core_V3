package com.lordofrobots.lorcoretest;

import android.hardware.usb.UsbDeviceConnection;
import com.hoho.android.usbserial.driver.UsbSerialPort;
import java.io.ByteArrayOutputStream;

final class UsbTransport implements AutoCloseable {
    private final UsbDeviceConnection connection;
    private final UsbSerialPort port;
    private long bytesWritten;
    private long bytesRead;

    UsbTransport(UsbDeviceConnection connection, UsbSerialPort port) throws Exception {
        this.connection = connection;
        this.port = port;
        port.open(connection);
        port.setFlowControl(UsbSerialPort.FlowControl.NONE);
        configure(115200);
        setLines(false, false);
        Thread.sleep(150);
    }

    synchronized void configure(int baud) throws Exception {
        port.setParameters(baud, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE);
    }

    synchronized void write(byte[] data) throws Exception {
        port.write(data, data.length, 5000);
        bytesWritten += data.length;
    }

    synchronized byte[] readSome(int maximum, int timeoutMs) throws Exception {
        byte[] buffer = new byte[maximum];
        int count = port.read(buffer, timeoutMs);
        if (count <= 0) return new byte[0];
        bytesRead += count;
        return java.util.Arrays.copyOf(buffer, count);
    }

    // Called synchronously by the native Espressif flasher bridge.
    synchronized byte[] nativeRead(int maximum, int timeoutMs) throws Exception {
        return readSome(maximum, timeoutMs);
    }

    synchronized void drain() {
        try { while (port.read(new byte[1024], 20) > 0) { } } catch (Exception ignored) { }
    }

    synchronized void setLines(boolean dtr, boolean rts) throws Exception {
        port.setDTR(dtr);
        port.setRTS(rts);
    }

    synchronized String diagnostics() {
        return "driver=" + port.getDriver().getClass().getSimpleName()
                + ", tx=" + bytesWritten + " bytes, rx=" + bytesRead + " bytes"
                + ", OUT=0x" + Integer.toHexString(port.getWriteEndpoint().getAddress())
                + ", IN=0x" + Integer.toHexString(port.getReadEndpoint().getAddress());
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
