package com.lordofrobots.lorcoretest;

import android.app.*;
import android.annotation.SuppressLint;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.hardware.usb.*;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import com.hoho.android.usbserial.driver.*;
import org.json.*;
import java.text.SimpleDateFormat;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

public final class MainActivity extends Activity {
    private static final String USB_PERMISSION = "com.lordofrobots.lorcoretest.USB_PERMISSION";
    private static final int EXPORT_CSV = 4102;
    private static final int BLUE = Color.rgb(3, 47, 130), GREEN = Color.rgb(24, 169, 87), RED = Color.rgb(223, 69, 69);
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private UsbManager usbManager;
    private UsbSerialDriver detectedDriver;
    private UsbTransport activeTransport;
    private CsvStore csvStore;
    private LinearLayout body, livePage, historyPage, resultList, historyList;
    private TextView connectionText, instructionText, percentText, historyDetails, firmwareText;
    private Button runButton, ledGoodButton, ledFailButton, liveTab, historyTab;
    private ProgressBar progress;
    private Switch autoStart;
    private EditText operatorInput, labelInput, vinInput, toleranceInput, ssidInput, rssiInput;
    private volatile boolean running;
    private CountDownLatch ledLatch;
    private volatile Boolean ledAnswer;
    private int armedDeviceId = -1;
    private Runnable pendingAutoStart;

    private final BroadcastReceiver usbReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (USB_PERMISSION.equals(action)) {
                UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) onUsbReady(device);
                else setConnection("USB permission was not granted", false);
            } else if (UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(action)) refreshUsb(true);
            else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(action)) {
                UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                if (device != null && device.getDeviceId() == armedDeviceId) cancelAutoStart();
                refreshUsb(false);
            }
        }
    };

    @SuppressLint("UnspecifiedRegisterReceiverFlag")
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        usbManager = (UsbManager) getSystemService(USB_SERVICE);
        csvStore = new CsvStore(this);
        buildUi();
        IntentFilter filter = new IntentFilter();
        filter.addAction(USB_PERMISSION);
        filter.addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED);
        filter.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(usbReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(usbReceiver, filter);
        refreshUsb(getIntent() != null && UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(getIntent().getAction()));
    }

    @Override protected void onNewIntent(Intent intent) { super.onNewIntent(intent); setIntent(intent); refreshUsb(true); }
    @Override protected void onDestroy() {
        try { unregisterReceiver(usbReceiver); } catch (Exception ignored) { }
        closeTransport(); worker.shutdownNow(); super.onDestroy();
    }

    private void buildUi() {
        getWindow().setStatusBarColor(BLUE);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(Color.rgb(243,246,250));
        root.setPadding(dp(24), dp(16), dp(24), dp(18)); setContentView(root);

        LinearLayout header = new LinearLayout(this); header.setOrientation(LinearLayout.VERTICAL); root.addView(header, lp(-1, dp(104)));
        LinearLayout brandRow = row(); brandRow.setGravity(Gravity.CENTER_VERTICAL); header.addView(brandRow, lp(-1, dp(54)));
        ImageView logo = new ImageView(this); logo.setImageResource(com.lordofrobots.lorcoretest.R.drawable.lor_logo); logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        brandRow.addView(logo, lp(dp(154), -1));
        TextView title = text("CORE V3  ·  " + BuildConfig.VERSION_NAME, 13, BLUE, true); title.setGravity(Gravity.END | Gravity.CENTER_VERTICAL); title.setSingleLine(true); brandRow.addView(title, weight(1));
        LinearLayout controlRow = row(); controlRow.setGravity(Gravity.CENTER_VERTICAL); header.addView(controlRow, lp(-1, dp(50)));
        connectionText = pill("NO BOARD", Color.rgb(102,117,138)); controlRow.addView(connectionText, weight(1));
        autoStart = new Switch(this); autoStart.setText(" AUTO-START"); autoStart.setTextColor(BLUE); autoStart.setTextSize(13); autoStart.setChecked(getPreferences(0).getBoolean("auto", true));
        autoStart.setOnCheckedChangeListener((v, checked) -> { getPreferences(0).edit().putBoolean("auto", checked).apply(); if (!checked) cancelAutoStart(); }); controlRow.addView(autoStart, lp(dp(150), dp(48)));

        LinearLayout tabs = row(); root.addView(tabs, lp(-1, dp(50)));
        liveTab = button("LIVE TEST", BLUE); historyTab = button("TEST HISTORY", Color.rgb(102,117,138));
        liveTab.setOnClickListener(v -> showPage(true)); historyTab.setOnClickListener(v -> showPage(false));
        tabs.addView(liveTab, weight(1)); tabs.addView(space(dp(10), 1)); tabs.addView(historyTab, weight(1));
        firmwareText = text("APK " + BuildConfig.VERSION_NAME + "  •  SHARED FIRMWARE", 12, Color.rgb(102,117,138), false);
        firmwareText.setGravity(Gravity.END | Gravity.CENTER_VERTICAL);

        body = new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL); root.addView(body, vWeight(1));
        livePage = buildLivePage(); historyPage = buildHistoryPage(); showPage(true);
    }

    private LinearLayout buildLivePage() {
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        LinearLayout active = card(); active.setPadding(dp(18),dp(14),dp(18),dp(14)); page.addView(active, lp(-1, dp(330)));
        active.addView(text("LIVE PRODUCTION TEST", 13, BLUE, true));
        instructionText = text("Connect the LoR Core with USB-C and apply the 6–12 V fixture supply.", 21, Color.rgb(20,36,58), true);
        instructionText.setGravity(Gravity.CENTER_VERTICAL); instructionText.setPadding(0,dp(5),0,dp(5)); active.addView(instructionText, lp(-1, dp(100)));
        LinearLayout progressRow = row(); progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal); progress.setMax(100); progress.setProgressTintList(android.content.res.ColorStateList.valueOf(BLUE));
        progressRow.addView(progress, weight(1)); percentText = text("0%", 13, BLUE, true); percentText.setGravity(Gravity.END|Gravity.CENTER_VERTICAL); progressRow.addView(percentText, lp(dp(52),dp(30))); active.addView(progressRow, lp(-1,dp(34)));
        LinearLayout ledRow = row(); ledGoodButton = button("LEDS LOOK GOOD", GREEN); ledFailButton = button("LED FAILURE", RED); ledGoodButton.setVisibility(View.GONE); ledFailButton.setVisibility(View.GONE);
        ledGoodButton.setOnClickListener(v -> answerLed(true)); ledFailButton.setOnClickListener(v -> answerLed(false)); ledRow.addView(ledGoodButton, weight(1)); ledRow.addView(space(dp(8),1)); ledRow.addView(ledFailButton, weight(1)); active.addView(ledRow, lp(-1,dp(48)));
        ScrollView resultsScroll = new ScrollView(this); resultList = new LinearLayout(this); resultList.setOrientation(LinearLayout.VERTICAL); resultsScroll.addView(resultList); active.addView(resultsScroll, vWeight(1));

        page.addView(space(1,dp(12)));
        LinearLayout setup = card(); setup.setPadding(dp(18),dp(14),dp(18),dp(14)); page.addView(setup, vWeight(1));
        setup.addView(text("TEST SETUP", 13, BLUE, true));
        ScrollView setupScroll = new ScrollView(this); setupScroll.setFillViewport(true);
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL); setupScroll.addView(form); setup.addView(setupScroll, vWeight(1));
        operatorInput = field(form, "Operator", ""); labelInput = field(form, "Board serial / label", "");
        LinearLayout voltage = row(); form.addView(voltage, lp(-1, dp(70)));
        vinInput = miniField(voltage, "Fixture VIN", "9.0"); toleranceInput = miniField(voltage, "Tolerance", "3.0");
        ssidInput = field(form, "Factory Wi-Fi SSID (optional)", ""); rssiInput = field(form, "Minimum RSSI (dBm)", "-85");
        runButton = button("CONNECT A LoR CORE", Color.rgb(150,160,174)); runButton.setEnabled(false); runButton.setTextSize(18); runButton.setOnClickListener(v -> startTest());
        setup.addView(runButton, marginLp(-1, dp(64), 0, dp(10), 0, 0));

        return page;
    }

    private LinearLayout buildHistoryPage() {
        LinearLayout page = new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL);
        LinearLayout left = card(); left.setPadding(dp(16),dp(14),dp(16),dp(14)); page.addView(left, lp(-1,dp(280)));
        LinearLayout heading = row(); heading.setGravity(Gravity.CENTER_VERTICAL); heading.addView(text("SAVED TESTS",13,BLUE,true), weight(1));
        Button export = button("EXPORT CSV", BLUE); export.setOnClickListener(v -> beginExport()); heading.addView(export, lp(dp(140),dp(42))); left.addView(heading, lp(-1,dp(50)));
        ScrollView historyScroll = new ScrollView(this); historyList = new LinearLayout(this); historyList.setOrientation(LinearLayout.VERTICAL); historyScroll.addView(historyList); left.addView(historyScroll, vWeight(1));
        page.addView(space(1,dp(12)));
        LinearLayout right = card(); right.setPadding(dp(18),dp(14),dp(18),dp(14)); page.addView(right, vWeight(1)); right.addView(text("TEST DETAILS",13,BLUE,true));
        historyDetails = text("Select a saved board test.",16,Color.rgb(20,36,58),false); historyDetails.setTextIsSelectable(true); historyDetails.setPadding(0,dp(14),0,0);
        ScrollView detailsScroll = new ScrollView(this); detailsScroll.addView(historyDetails); right.addView(detailsScroll, vWeight(1));
        return page;
    }

    private void showPage(boolean live) {
        body.removeAllViews(); body.addView(live ? livePage : historyPage, vWeight(1));
        liveTab.setBackground(bg(live ? BLUE : Color.rgb(102,117,138), 12)); historyTab.setBackground(bg(live ? Color.rgb(102,117,138) : BLUE, 12));
        if (!live) loadHistory();
    }

    private void refreshUsb(boolean request) {
        detectedDriver = null;
        for (UsbSerialDriver driver : UsbSerialProber.getDefaultProber().findAllDrivers(usbManager)) {
            if (driver.getDevice().getVendorId() == 0x1A86) { detectedDriver = driver; break; }
        }
        if (detectedDriver == null) { setConnection("NO BOARD", false); return; }
        UsbDevice device = detectedDriver.getDevice();
        if (usbManager.hasPermission(device)) onUsbReady(device);
        else if (request) {
            PendingIntent permission = PendingIntent.getBroadcast(this, 0, new Intent(USB_PERMISSION).setPackage(getPackageName()), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE);
            usbManager.requestPermission(device, permission); setConnection("USB PERMISSION", false);
        } else { setConnection("BOARD DETECTED", false); requestUsbPermission(device); }
    }

    private void requestUsbPermission(UsbDevice device) {
        runButton.setText("GRANT USB ACCESS"); runButton.setEnabled(true); runButton.setBackground(bg(BLUE,14));
        runButton.setOnClickListener(v -> {
            PendingIntent permission = PendingIntent.getBroadcast(this, 0, new Intent(USB_PERMISSION).setPackage(getPackageName()), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE);
            usbManager.requestPermission(device, permission);
        });
    }

    private void onUsbReady(UsbDevice device) {
        setConnection("LoR CORE READY", true); runButton.setText("RUN PRODUCTION TEST"); runButton.setEnabled(!running); runButton.setBackground(bg(GREEN,14)); runButton.setOnClickListener(v -> startTest());
        if (autoStart.isChecked() && !running && armedDeviceId != device.getDeviceId()) {
            cancelAutoStart();
            final int deviceId = device.getDeviceId();
            armedDeviceId = deviceId;
            pendingAutoStart = () -> {
                pendingAutoStart = null;
                if (autoStart.isChecked() && !running && detectedDriver != null && detectedDriver.getDevice().getDeviceId() == deviceId) startTest();
            };
            runButton.postDelayed(pendingAutoStart, 1200);
        }
    }

    private void cancelAutoStart() {
        if (pendingAutoStart != null && runButton != null) runButton.removeCallbacks(pendingAutoStart);
        pendingAutoStart = null;
        armedDeviceId = -1;
    }

    private void setConnection(String text, boolean ready) {
        connectionText.setText(text); connectionText.setBackground(bg(ready ? GREEN : Color.rgb(102,117,138), 20));
        if (!ready && !running) { runButton.setText("CONNECT A LoR CORE"); runButton.setEnabled(false); runButton.setBackground(bg(Color.rgb(150,160,174),14)); }
    }

    private void startTest() {
        if (running || detectedDriver == null || !usbManager.hasPermission(detectedDriver.getDevice())) return;
        final double target, tolerance; final int rssi;
        try { target = Double.parseDouble(vinInput.getText().toString()); tolerance = Double.parseDouble(toleranceInput.getText().toString()); rssi = Integer.parseInt(rssiInput.getText().toString()); }
        catch (Exception error) { toast("Check the VIN, tolerance, and RSSI settings."); return; }
        if (tolerance <= 0) { toast("VIN tolerance must be greater than zero."); return; }
        running = true; runButton.setEnabled(false); resultList.removeAllViews(); progress.setProgress(0); percentText.setText("0%"); showPage(true);
        String operator = operatorInput.getText().toString().trim(), label = labelInput.getText().toString().trim(), ssid = ssidInput.getText().toString().trim();
        worker.submit(() -> runProductionTest(operator, label, target, tolerance, ssid, rssi));
    }

    private void runProductionTest(String operator, String label, double target, double tolerance, String ssid, int minRssi) {
        Map<String,String> record = blankRecord(); JSONArray details = new JSONArray(); BoardSession board = null;
        record.put("timestamp_utc", Instant.now().toString()); record.put("operator", operator); record.put("serial_label", label); record.put("com_port", "USB/CH340 Android"); record.put("control_mapping", "Confirmed LoR Core V3 mapping");
        try {
            FirmwareRepository.Package firmware = new FirmwareRepository(this).loadBundled();
            ui(() -> firmwareText.setText("APK " + BuildConfig.VERSION_NAME + "  •  FW " + firmware.version.replace("production-test-", "")));
            status("Uploading verified production firmware...");
            UsbDeviceConnection connection = usbManager.openDevice(detectedDriver.getDevice());
            if (connection == null) throw new IllegalStateException("Android could not open the USB device");
            activeTransport = new UsbTransport(connection, detectedDriver.getPorts().get(0));
            new Esp32Flasher(activeTransport, new Esp32Flasher.Listener() {
                public void status(String text) { MainActivity.this.status(text); }
                public void progress(int value) { ui(() -> { progress.setProgress(value); percentText.setText(value + "%"); }); }
            }).flash(firmware.images);
            status("Waiting for the LoR Core startup animation..."); Thread.sleep(2900); activeTransport.drain(); board = new BoardSession(activeTransport);
            JSONObject info = board.info();
            if (!"LoR Core V3".equals(info.optString("product"))) throw new IllegalStateException("Programmed device did not return the LoR Core V3 handshake");
            record.put("board_id", info.optString("mac")); record.put("firmware", info.optString("firmware")); record.put("chip", info.optString("chip")); record.put("chip_revision", info.optString("revision")); record.put("flash_bytes", info.optString("flash_bytes"));
            addResult(details, "Board identity", true, "ID " + record.get("board_id") + " / " + record.get("firmware"));
            board.result("TEST_START", "TEST_START", 5000);

            status("Reading the 20-sample battery voltage average...");
            JSONObject vin = board.result(String.format(Locale.US,"VIN %.3f %.3f", target-tolerance, target+tolerance), "VIN", 8000); Map<String,String> vd = BoardSession.details(vin.optString("details"));
            record.put("vin_volts",vd.getOrDefault("volts","")); record.put("vin_pass",Boolean.toString(vin.optBoolean("pass"))); addResult(details,"Battery voltage",vin.optBoolean("pass"),vin.optString("details"));

            status("Scanning Wi-Fi and measuring RSSI..."); String wifiCommand = ssid.isEmpty() ? "WIFI " + minRssi : "WIFI " + ssid + " " + minRssi;
            JSONObject wifi = board.result(wifiCommand,"WIFI",25000); Map<String,String> wd=BoardSession.details(wifi.optString("details"));
            record.put("wifi_pass",Boolean.toString(wifi.optBoolean("pass"))); record.put("wifi_networks",wd.getOrDefault("networks","")); record.put("wifi_target",wd.getOrDefault("target","")); record.put("wifi_rssi_dbm",wd.getOrDefault("rssi_dbm","")); addResult(details,"Wi-Fi / RSSI",wifi.optBoolean("pass"),wifi.optString("details"));

            status("Checking the ESP32 Bluetooth controller..."); JSONObject bt=board.result("BT","BLUETOOTH",12000); record.put("bluetooth_pass",Boolean.toString(bt.optBoolean("pass"))); addResult(details,"Bluetooth",bt.optBoolean("pass"),bt.optString("details"));
            board.result("LED_DEMO","LED_DEMO",8000); status("CHECK THE FOUR LEDS — confirm the rainbow startup and icy-blue spatial orb."); boolean ledOk = awaitLed(); record.put("led_pass",Boolean.toString(ledOk)); addResult(details,"Four RGB LEDs",ledOk,ledOk?"operator confirmed animation":"operator rejected or timed out");

            int[] pins={35,39,38,37,36}; String[] names={"BTN_A","BTN_B","BTN_C","BTN_D","SW"}; String[] prompts={"PRESS AND HOLD BUTTON A — LEDs turn YELLOW.","PRESS AND HOLD BUTTON B — LEDs turn GREEN.","PRESS AND HOLD BUTTON C — LEDs turn RED.","PRESS AND HOLD BUTTON D — LEDs turn BLUE.","TOGGLE THE USER SWITCH to its other position."};
            String[] fields={"btn_a_pass","btn_b_pass","btn_c_pass","btn_d_pass","switch_pass"};
            for(int i=0;i<pins.length;i++) {
                status(prompts[i]); Map<Integer,Integer> baseline=board.inputs(); boolean passed=false; List<Integer> changed=new ArrayList<>(); long deadline=System.currentTimeMillis()+18000;
                while(System.currentTimeMillis()<deadline) { Map<Integer,Integer> current=board.inputs(); changed.clear(); for(int pin:baseline.keySet()) if(!Objects.equals(baseline.get(pin),current.get(pin))) changed.add(pin); if(changed.contains(pins[i])) break; Thread.sleep(80); }
                passed=changed.size()==1&&changed.get(0)==pins[i]; record.put(fields[i],Boolean.toString(passed)); addResult(details,names[i].replace('_',' '),passed,"expected GPIO"+pins[i]+"; changed "+(changed.isEmpty()?"none":changed));
                if(i<4&&passed) { status("RELEASE "+names[i].replace('_',' ')+"."); long release=System.currentTimeMillis()+8000; while(System.currentTimeMillis()<release&&Objects.equals(board.inputs().get(pins[i]),1-baseline.get(pins[i]))) Thread.sleep(80); }
            }
            boolean overall=true; for(String field:new String[]{"vin_pass","wifi_pass","bluetooth_pass","btn_a_pass","btn_b_pass","btn_c_pass","btn_d_pass","switch_pass","led_pass"}) overall &= "true".equals(record.get(field));
            record.put("overall_pass",Boolean.toString(overall));
            if(overall) { status("PASS — LEDs green for two seconds, then return to icy blue."); board.result("TEST_PASS","TEST_PASS",6000); }
            else { status("FAIL — board LEDs are locked red across power cycles."); board.result("TEST_FAIL","TEST_FAIL",5000); }
            record.put("details_json",details.toString()); csvStore.append(record); complete(overall,record.get("board_id"));
        } catch(Exception error) {
            if(board!=null) try { board.result("TEST_FAIL","TEST_FAIL",4000); } catch(Exception ignored) { }
            try { record.put("overall_pass","false"); JSONObject row=new JSONObject(); row.put("test","Station error"); row.put("pass",false); row.put("details",error.getMessage()); details.put(row); record.put("details_json",details.toString()); csvStore.append(record); } catch(Exception ignored) { }
            ui(() -> { statusDirect("TEST STOPPED — " + (error.getMessage()==null?error.getClass().getSimpleName():error.getMessage()), RED); toast("Production test failed"); });
        } finally { closeTransport(); running=false; ui(() -> { hideLedButtons(); refreshUsb(false); loadHistory(); }); }
    }

    private boolean awaitLed() throws InterruptedException {
        ledAnswer=null; ledLatch=new CountDownLatch(1); ui(() -> { ledGoodButton.setVisibility(View.VISIBLE); ledFailButton.setVisibility(View.VISIBLE); });
        boolean answered=ledLatch.await(120,TimeUnit.SECONDS); ui(this::hideLedButtons); return answered&&Boolean.TRUE.equals(ledAnswer);
    }
    private void answerLed(boolean passed) { ledAnswer=passed; CountDownLatch latch=ledLatch; if(latch!=null) latch.countDown(); hideLedButtons(); }
    private void hideLedButtons() { ledGoodButton.setVisibility(View.GONE); ledFailButton.setVisibility(View.GONE); }

    private void addResult(JSONArray details,String name,boolean passed,String description) throws JSONException {
        JSONObject row=new JSONObject(); row.put("test",name); row.put("pass",passed); row.put("details",description); details.put(row);
        ui(() -> { LinearLayout card=new LinearLayout(this); card.setPadding(dp(14),dp(10),dp(14),dp(10)); card.setGravity(Gravity.CENTER_VERTICAL); card.setBackground(bg(Color.rgb(247,249,252),10));
            TextView mark=text(passed?"PASS":"FAIL",12,passed?GREEN:RED,true); card.addView(mark,lp(dp(58),dp(34))); LinearLayout words=new LinearLayout(this); words.setOrientation(LinearLayout.VERTICAL); words.addView(text(name,15,Color.rgb(20,36,58),true)); words.addView(text(description,12,Color.rgb(102,117,138),false)); card.addView(words,weight(1)); resultList.addView(card,marginLp(-1,-2,0,0,0,dp(7))); });
    }

    private Map<String,String> blankRecord(){ Map<String,String> r=new LinkedHashMap<>(); for(String f:CsvStore.FIELDS)r.put(f,""); return r; }
    private void status(String text){ ui(() -> statusDirect(text,BLUE)); }
    private void statusDirect(String text,int color){ instructionText.setText(text); instructionText.setTextColor(color); }
    private void complete(boolean passed,String id){ ui(() -> { progress.setProgress(100); percentText.setText("100%"); statusDirect((passed?"PASS":"FAIL")+" — Board "+id+" — CSV record saved",passed?GREEN:RED); }); }
    private void closeTransport(){ UsbTransport value=activeTransport; activeTransport=null; if(value!=null)value.close(); }

    private void loadHistory() {
        if(historyList==null)return; historyList.removeAllViews();
        try { for(Map<String,String> record:csvStore.load(2000)) {
            boolean passed="true".equalsIgnoreCase(record.get("overall_pass")); String board=record.getOrDefault("serial_label",""); if(board.isEmpty())board=record.getOrDefault("board_id","Unknown board");
            Button item=button((passed?"PASS  ":"FAIL  ")+board+"\n"+record.getOrDefault("timestamp_utc",""),passed?GREEN:RED); item.setGravity(Gravity.START|Gravity.CENTER_VERTICAL); item.setAllCaps(false); item.setOnClickListener(v -> showHistoryRecord(record)); historyList.addView(item,marginLp(-1,dp(58),0,0,0,dp(8))); }
        } catch(Exception error){ historyList.addView(text("History could not be loaded: "+error.getMessage(),14,RED,false)); }
    }
    private void showHistoryRecord(Map<String,String> record) {
        StringBuilder text=new StringBuilder(); text.append("BOARD\n").append(record.getOrDefault("board_id","—")).append("\n\nRESULT  ").append("true".equalsIgnoreCase(record.get("overall_pass"))?"PASS":"FAIL").append("\nTIMESTAMP  ").append(record.getOrDefault("timestamp_utc","—")).append("\nOPERATOR  ").append(record.getOrDefault("operator","—")).append("\nFIRMWARE  ").append(record.getOrDefault("firmware","—")).append("\n\nMEASUREMENTS\nVIN  ").append(record.getOrDefault("vin_volts","—")).append(" V\nWi-Fi RSSI  ").append(record.getOrDefault("wifi_rssi_dbm","—")).append(" dBm\nNetworks  ").append(record.getOrDefault("wifi_networks","—")).append("\n\nCHECKS\n");
        try { JSONArray rows=new JSONArray(record.getOrDefault("details_json","[]")); for(int i=0;i<rows.length();i++){JSONObject row=rows.getJSONObject(i); text.append(row.optBoolean("pass")?"✓ ":"✕ ").append(row.optString("test")).append("\n   ").append(row.optString("details")).append("\n");} } catch(Exception ignored){text.append(record.getOrDefault("details_json",""));}
        historyDetails.setText(text.toString());
    }

    private void beginExport(){ Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("text/csv").putExtra(Intent.EXTRA_TITLE,"lor_core_v3_results.csv"); startActivityForResult(intent,EXPORT_CSV); }
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data); if(request==EXPORT_CSV&&result==RESULT_OK&&data!=null&&data.getData()!=null)try{csvStore.exportTo(data.getData());toast("CSV exported");}catch(Exception e){toast("Export failed: "+e.getMessage());}}

    private LinearLayout row(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.HORIZONTAL);return v;}
    private LinearLayout card(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);v.setBackground(bg(Color.WHITE,16));v.setElevation(dp(2));return v;}
    private TextView text(String value,float size,int color,boolean bold){TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(color);if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return v;}
    private TextView pill(String value,int color){TextView v=text(value,12,Color.WHITE,true);v.setGravity(Gravity.CENTER);v.setBackground(bg(color,20));return v;}
    private Button button(String value,int color){Button v=new Button(this);v.setText(value);v.setTextColor(Color.WHITE);v.setTextSize(13);v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);v.setBackground(bg(color,12));v.setPadding(dp(12),0,dp(12),0);return v;}
    private EditText field(LinearLayout parent,String hint,String value){TextView label=text(hint.toUpperCase(Locale.US),11,Color.rgb(102,117,138),true);parent.addView(label,marginLp(-1,dp(22),0,dp(8),0,0));EditText edit=new EditText(this);edit.setSingleLine(true);edit.setText(value);edit.setTextSize(15);edit.setPadding(dp(12),0,dp(12),0);edit.setBackground(bg(Color.rgb(243,246,250),9));parent.addView(edit,lp(-1,dp(46)));return edit;}
    private EditText miniField(LinearLayout parent,String hint,String value){LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.addView(text(hint.toUpperCase(Locale.US),10,Color.rgb(102,117,138),true),lp(-1,dp(22)));EditText edit=new EditText(this);edit.setSingleLine(true);edit.setText(value);edit.setTextSize(14);edit.setPadding(dp(10),0,dp(10),0);edit.setBackground(bg(Color.rgb(243,246,250),9));box.addView(edit,lp(-1,dp(44)));parent.addView(box,marginWeight(1,0,dp(8),0,0));return edit;}
    private GradientDrawable bg(int color,float radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp((int)radius));return d;}
    private Space space(int w,int h){Space s=new Space(this);s.setLayoutParams(lp(w,h));return s;}
    private LinearLayout.LayoutParams lp(int w,int h){return new LinearLayout.LayoutParams(w,h);}
    private LinearLayout.LayoutParams weight(float value){return new LinearLayout.LayoutParams(0,-1,value);}
    private LinearLayout.LayoutParams vWeight(float value){return new LinearLayout.LayoutParams(-1,0,value);}
    private LinearLayout.LayoutParams marginWeight(float value,int l,int t,int r,int b){LinearLayout.LayoutParams p=weight(value);p.setMargins(l,t,r,b);return p;}
    private LinearLayout.LayoutParams marginLp(int w,int h,int l,int t,int r,int b){LinearLayout.LayoutParams p=lp(w,h);p.setMargins(l,t,r,b);return p;}
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private void ui(Runnable action){runOnUiThread(action);}
    private void toast(String message){Toast.makeText(this,message,Toast.LENGTH_LONG).show();}
}
