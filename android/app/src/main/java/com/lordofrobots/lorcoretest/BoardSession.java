package com.lordofrobots.lorcoretest;

import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

final class BoardSession {
    private final UsbTransport serial;
    BoardSession(UsbTransport serial) { this.serial = serial; }

    JSONObject command(String command, String expectedType, String expectedTest, long timeoutMs) throws Exception {
        serial.write((command + "\n").getBytes(StandardCharsets.UTF_8));
        long deadline = System.currentTimeMillis() + timeoutMs;
        while (System.currentTimeMillis() < deadline) {
            String line;
            try { line = serial.readLine(Math.min(800, Math.max(100, deadline - System.currentTimeMillis()))); }
            catch (java.util.concurrent.TimeoutException ignored) { continue; }
            if (!line.startsWith("{")) continue;
            JSONObject message;
            try { message = new JSONObject(line); } catch (Exception ignored) { continue; }
            if (!expectedType.equals(message.optString("type"))) continue;
            if (expectedTest != null && !expectedTest.equals(message.optString("test"))) continue;
            return message;
        }
        throw new java.util.concurrent.TimeoutException("Board did not answer " + command);
    }

    JSONObject info() throws Exception { return command("INFO", "info", null, 8000); }
    JSONObject result(String command, String test, long timeoutMs) throws Exception { return command(command, "result", test, timeoutMs); }

    Map<Integer, Integer> inputs() throws Exception {
        JSONObject message = command("INPUTS", "inputs", null, 3000);
        Map<Integer, Integer> values = new HashMap<>();
        for (int pin : new int[]{35, 36, 37, 38, 39}) values.put(pin, message.getInt("gpio" + pin));
        return values;
    }

    static Map<String, String> details(String text) {
        Map<String, String> values = new HashMap<>();
        for (String item : text.split(",")) {
            int split = item.indexOf('=');
            if (split > 0) values.put(item.substring(0, split).trim(), item.substring(split + 1).trim());
        }
        return values;
    }
}
