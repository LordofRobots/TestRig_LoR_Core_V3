package com.lordofrobots.lorcoretest;

import android.content.Context;
import android.net.Uri;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

final class CsvStore {
    static final String[] FIELDS = {
        "timestamp_utc", "operator", "serial_label", "board_id", "com_port", "firmware",
        "chip", "chip_revision", "flash_bytes", "vin_volts", "vin_pass", "wifi_pass",
        "wifi_networks", "wifi_target", "wifi_rssi_dbm", "bluetooth_pass", "btn_a_pass",
        "btn_b_pass", "btn_c_pass", "btn_d_pass", "switch_pass", "led_pass",
        "overall_pass", "control_mapping", "details_json"
    };
    private final Context context;
    private final File file;
    CsvStore(Context context) {
        this.context = context.getApplicationContext();
        File dir = new File(context.getFilesDir(), "results");
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        file = new File(dir, "lor_core_v3_results.csv");
    }

    synchronized void append(Map<String, String> record) throws IOException {
        boolean header = !file.exists() || file.length() == 0;
        try (Writer writer = new OutputStreamWriter(new FileOutputStream(file, true), StandardCharsets.UTF_8)) {
            if (header) writeRow(writer, Arrays.asList(FIELDS));
            List<String> row = new ArrayList<>();
            for (String field : FIELDS) row.add(record.getOrDefault(field, ""));
            writeRow(writer, row);
        }
    }

    synchronized List<Map<String, String>> load(int limit) throws IOException {
        List<Map<String, String>> records = new ArrayList<>();
        if (!file.exists()) return records;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(file), StandardCharsets.UTF_8))) {
            String headerLine = reader.readLine();
            if (headerLine == null) return records;
            List<String> headers = parseRow(headerLine);
            for (String line; (line = reader.readLine()) != null;) {
                List<String> cells = parseRow(line);
                Map<String, String> record = new LinkedHashMap<>();
                for (int i = 0; i < headers.size(); i++) record.put(headers.get(i), i < cells.size() ? cells.get(i) : "");
                records.add(record);
                if (records.size() > limit) records.remove(0);
            }
        }
        Collections.reverse(records);
        return records;
    }

    synchronized void exportTo(Uri destination) throws IOException {
        try (InputStream input = file.exists() ? new FileInputStream(file) : new ByteArrayInputStream(String.join(",", FIELDS).getBytes(StandardCharsets.UTF_8));
             OutputStream output = context.getContentResolver().openOutputStream(destination, "wt")) {
            if (output == null) throw new IOException("Android did not provide the selected export file");
            byte[] buffer = new byte[32768];
            for (int n; (n = input.read(buffer)) >= 0;) output.write(buffer, 0, n);
        }
    }

    File location() { return file; }

    private static void writeRow(Writer writer, List<String> values) throws IOException {
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) writer.write(',');
            String value = values.get(i) == null ? "" : values.get(i);
            writer.write('"'); writer.write(value.replace("\"", "\"\"")); writer.write('"');
        }
        writer.write("\r\n");
    }

    private static List<String> parseRow(String line) {
        List<String> result = new ArrayList<>();
        StringBuilder cell = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                if (quoted && i + 1 < line.length() && line.charAt(i + 1) == '"') { cell.append('"'); i++; }
                else quoted = !quoted;
            } else if (c == ',' && !quoted) { result.add(cell.toString()); cell.setLength(0); }
            else cell.append(c);
        }
        result.add(cell.toString());
        return result;
    }
}
