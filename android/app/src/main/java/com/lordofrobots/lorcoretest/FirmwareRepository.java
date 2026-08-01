package com.lordofrobots.lorcoretest;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

final class FirmwareRepository {
    static final class Image {
        final int address;
        final String name;
        final byte[] data;
        Image(int address, String name, byte[] data) {
            this.address = address; this.name = name; this.data = data;
        }
    }
    static final class Package {
        final String version;
        final List<Image> images;
        Package(String version, List<Image> images) { this.version = version; this.images = images; }
    }

    private final Context context;
    FirmwareRepository(Context context) { this.context = context.getApplicationContext(); }

    Package loadBundled() throws Exception {
        JSONObject manifest = new JSONObject(new String(readAsset("firmware/lor-core-v3-firmware-manifest.json"), java.nio.charset.StandardCharsets.UTF_8));
        if (manifest.optInt("schema") != 1 || !"LoR Core V3".equals(manifest.optString("product")) || manifest.optInt("protocol") != 1) {
            throw new SecurityException("Firmware manifest identity or protocol is invalid");
        }
        int[] approved = {0x1000, 0x8000, 0xe000, 0x10000};
        JSONArray files = manifest.getJSONArray("files");
        if (files.length() != approved.length) throw new SecurityException("Firmware layout is incomplete");
        List<Image> images = new ArrayList<>();
        for (int i = 0; i < files.length(); i++) {
            JSONObject item = files.getJSONObject(i);
            int address = Integer.decode(item.getString("address"));
            if (address != approved[i]) throw new SecurityException("Firmware flash address is not approved");
            String name = item.getString("name");
            if (name.contains("/") || name.contains("\\") || name.contains("..")) throw new SecurityException("Unsafe firmware filename");
            byte[] data = readAsset("firmware/" + name);
            if (!sha256(data).equalsIgnoreCase(item.getString("sha256"))) throw new SecurityException("Firmware hash failed: " + name);
            images.add(new Image(address, name, data));
        }
        return new Package(manifest.getString("version"), images);
    }

    private byte[] readAsset(String path) throws Exception {
        try (InputStream input = context.getAssets().open(path); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[32768];
            for (int n; (n = input.read(buffer)) >= 0;) output.write(buffer, 0, n);
            return output.toByteArray();
        }
    }

    private static String sha256(byte[] data) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder text = new StringBuilder(64);
        for (byte value : digest) text.append(String.format(Locale.US, "%02X", value & 0xff));
        return text.toString();
    }
}
