#!/usr/bin/env python3
"""LoR Core V3 production test station (Tkinter desktop UI)."""

from __future__ import annotations

import csv
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:
    raise SystemExit("pyserial is required. Run: python -m pip install pyserial") from exc


ROOT = Path(__file__).resolve().parents[1]
SKETCH = ROOT / "production_test" / "lor_core_v3_production_test"
BUILD = ROOT / "build" / "lor_core_v3_production_test"
CSV_FILE = ROOT / "production_test" / "results" / "lor_core_v3_results.csv"
FQBN = "esp32:esp32:esp32"
ARDUINO_CLI_FALLBACK = Path(r"C:\Program Files\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe")
ASSET_DIR = ROOT / "production_test" / "assets"
BRAND_GIF = ASSET_DIR / "lor-logo-animated.gif"
APP_ICON = ASSET_DIR / "lor-test-station.ico"

BRAND_BLUE = "#032F82"
BRAND_BLUE_LIGHT = "#0B49B5"
APP_BACKGROUND = "#F3F6FA"
SURFACE = "#FFFFFF"
TEXT_PRIMARY = "#14243A"
TEXT_MUTED = "#66758A"
BORDER = "#DDE5EF"
SUCCESS = "#18A957"
FAILURE = "#DF4545"

CONTROL_MAPPING_NAME = "Confirmed LoR Core V3 mapping"
CONTROL_MAPPING = {"BTN_A": 35, "BTN_B": 39, "BTN_C": 38, "BTN_D": 37, "SW": 36}

CSV_FIELDS = [
    "timestamp_utc", "operator", "serial_label", "board_id", "com_port", "firmware",
    "chip", "chip_revision", "flash_bytes", "vin_volts", "vin_pass", "wifi_pass",
    "wifi_networks", "wifi_target", "wifi_rssi_dbm", "bluetooth_pass", "btn_a_pass",
    "btn_b_pass", "btn_c_pass", "btn_d_pass", "switch_pass", "led_pass",
    "overall_pass", "control_mapping", "details_json",
]


def find_arduino_cli() -> str:
    found = shutil.which("arduino-cli")
    if found:
        return found
    if ARDUINO_CLI_FALLBACK.exists():
        return str(ARDUINO_CLI_FALLBACK)
    raise FileNotFoundError("arduino-cli was not found. Install Arduino IDE 2.x or put arduino-cli on PATH.")


def parse_details(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in text.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parsed[key.strip()] = value.strip()
    return parsed


def canonical_board_id(value: str) -> str:
    """Format current IDs and normalize legacy byte-reversed CSV IDs."""
    value = value.strip()
    compact = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(compact) != 12:
        return value
    if ":" not in value and "-" not in value:
        octets = [compact[index:index + 2] for index in range(0, 12, 2)]
        octets.reverse()
    else:
        octets = [compact[index:index + 2] for index in range(0, 12, 2)]
    return ":".join(octet.upper() for octet in octets)


def format_test_details(test_name: str, details: str) -> str:
    values = parse_details(details)
    if test_name == "Battery voltage" and values.get("volts"):
        parts = [f"{values['volts']} V"]
        if values.get("raw_adc"):
            parts.append(f"raw ADC {values['raw_adc']} avg")
        if values.get("min") and values.get("max"):
            parts.append(f"accepted {values['min']}–{values['max']} V")
        return "  •  ".join(parts)
    if test_name == "Wi-Fi / RSSI" and values:
        parts = []
        if values.get("rssi_dbm"):
            parts.append(f"{values['rssi_dbm']} dBm")
        if values.get("networks"):
            parts.append(f"{values['networks']} networks")
        if values.get("min_rssi_dbm"):
            parts.append(f"minimum {values['min_rssi_dbm']} dBm")
        if values.get("target"):
            parts.append(values["target"])
        return "  •  ".join(parts)
    if test_name in ("Bluetooth", "BLUETOOTH") and values:
        parts = []
        if values.get("best_rssi_dbm"):
            parts.append(f"strongest {values['best_rssi_dbm']} dBm")
        if values.get("devices"):
            parts.append(f"{values['devices']} devices")
        if values.get("best_device"):
            parts.append(values["best_device"])
        return "  •  ".join(parts)
    return details.replace(";", "  •  ").replace(",", "  •  ")


def firmware_needs_compile() -> bool:
    binary = BUILD / "lor_core_v3_production_test.ino.bin"
    if not binary.exists():
        return True
    newest_source = max(path.stat().st_mtime for path in SKETCH.rglob("*") if path.is_file())
    return newest_source > binary.stat().st_mtime


def list_candidate_ports() -> list[tuple[str, str]]:
    ports = list(list_ports.comports())
    preferred = []
    for port in ports:
        description = f"{port.description} {port.manufacturer or ''} {port.hwid}".lower()
        if port.vid == 0x1A86 or "ch340" in description or "ch341" in description or "wch" in description:
            preferred.append((port.device, port.description))
    selected = preferred or [(port.device, port.description) for port in ports]
    return sorted(selected, key=lambda item: item[0])


class Dut:
    def __init__(self, port: str):
        deadline = time.monotonic() + 25
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                self.serial = serial.Serial(port, 115200, timeout=0.35, write_timeout=2)
                time.sleep(1.0)
                self.serial.reset_input_buffer()
                return
            except (serial.SerialException, OSError) as exc:
                last_error = exc
                time.sleep(0.5)
        raise ConnectionError(f"Could not open {port} after upload: {last_error}")

    def close(self) -> None:
        self.serial.close()

    def send(self, command: str) -> None:
        self.serial.write((command + "\n").encode("utf-8"))
        self.serial.flush()

    def read_json(self, timeout: float) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.serial.readline().decode("utf-8", errors="replace").strip()
            if not raw.startswith("{"):
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue
        return None

    def command(self, command: str, predicate, timeout: float = 15.0) -> dict:
        self.send(command)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.read_json(max(0.1, deadline - time.monotonic()))
            if message is not None and predicate(message):
                return message
        raise TimeoutError(f"No valid response to {command!r}")

    def inputs(self) -> dict[int, int]:
        message = self.command("INPUTS", lambda m: m.get("type") == "inputs", 3)
        return {pin: int(message[f"gpio{pin}"]) for pin in (35, 36, 37, 38, 39)}


class TestStation:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LoR Core V3 Production Test Station")
        self.root.geometry("1240x800")
        self.root.minsize(1040, 700)
        if APP_ICON.exists():
            self.root.iconbitmap(str(APP_ICON))
        self.events: queue.Queue[tuple] = queue.Queue()
        self.running = False
        self.led_answer: bool | None = None
        self.led_event = threading.Event()
        self.port_descriptions: dict[str, str] = {}
        self.last_ports: tuple[str, ...] = ()
        self.activity_token = 0
        self.activity_text = ""
        self.activity_percent: int | None = None
        self.logo_frame_index = 0
        self.advanced_visible = False
        self._build_ui()
        self.root.after(100, self._drain_events)
        self.root.after(100, self._poll_ports)
        self.root.after(45, self._animate_brand_logo)

    def _build_ui(self) -> None:
        self.root.configure(bg=APP_BACKGROUND)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=APP_BACKGROUND)
        style.configure("TLabel", background=APP_BACKGROUND, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
        style.configure(
            "Modern.TEntry", fieldbackground="#F7F9FC", foreground=TEXT_PRIMARY,
            bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=8,
        )
        style.configure(
            "Modern.TCombobox", fieldbackground="#F7F9FC", foreground=TEXT_PRIMARY,
            bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=7,
        )
        style.map("Modern.TCombobox", fieldbackground=[("readonly", "#F7F9FC")], foreground=[("readonly", TEXT_PRIMARY)])
        style.configure(
            "Treeview", background=SURFACE, foreground=TEXT_PRIMARY, fieldbackground=SURFACE,
            borderwidth=0, rowheight=34, font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading", background="#EDF2F8", foreground=TEXT_MUTED,
            borderwidth=0, relief="flat", font=("Segoe UI Semibold", 9), padding=(10, 9),
        )
        style.map("Treeview", background=[("selected", "#E7F0FF")], foreground=[("selected", BRAND_BLUE)])
        style.configure("Modern.TNotebook", background=APP_BACKGROUND, borderwidth=0, tabmargins=0)
        style.configure(
            "Modern.TNotebook.Tab", background="#E7ECF3", foreground=TEXT_MUTED,
            font=("Segoe UI Semibold", 10), padding=(18, 10), borderwidth=0,
        )
        style.map(
            "Modern.TNotebook.Tab", background=[("selected", SURFACE)],
            foreground=[("selected", BRAND_BLUE)],
        )
        style.configure(
            "Factory.Horizontal.TProgressbar", troughcolor="#E3EAF3", background=BRAND_BLUE_LIGHT,
            lightcolor=BRAND_BLUE_LIGHT, darkcolor=BRAND_BLUE, bordercolor="#E3EAF3", thickness=10,
        )

        self.port_var = tk.StringVar()
        self.serial_var = tk.StringVar()
        self.operator_var = tk.StringVar()
        self.vin_var = tk.StringVar(value="9.0")
        self.tolerance_var = tk.StringVar(value="3.0")
        self.ssid_var = tk.StringVar()
        self.rssi_var = tk.StringVar(value="-85")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        sidebar = tk.Frame(self.root, bg=BRAND_BLUE, width=280)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        try:
            self.logo_image = tk.PhotoImage(file=str(BRAND_GIF), format="gif -index 0")
            self.logo_label = tk.Label(sidebar, image=self.logo_image, bg=BRAND_BLUE, bd=0)
            self.logo_label.pack(pady=(28, 6))
        except tk.TclError:
            self.logo_image = None
            self.logo_label = tk.Label(sidebar, text="LORD\nOF ROBOTS", bg=BRAND_BLUE, fg="white", font=("Segoe UI Semibold", 24), justify="left")
            self.logo_label.pack(anchor="w", padx=28, pady=(40, 20))

        tk.Label(
            sidebar, text="PRODUCTION TEST STATION", bg=BRAND_BLUE, fg="#AFC7F5",
            font=("Segoe UI Semibold", 9), padx=24,
        ).pack(anchor="w")
        tk.Frame(sidebar, bg="#2B55A0", height=1).pack(fill="x", padx=24, pady=24)

        self.connection_label = tk.Label(
            sidebar, text="WAITING FOR BOARD", bg=BRAND_BLUE, fg="#BED0EF",
            font=("Segoe UI Semibold", 11), justify="left", anchor="w", wraplength=224,
        )
        self.connection_label.pack(fill="x", padx=28)

        tk.Label(
            sidebar, text="Connect the LoR Core over USB-C, then run the guided production check.",
            bg=BRAND_BLUE, fg="#91ADDD", font=("Segoe UI", 9), justify="left",
            anchor="w", wraplength=218,
        ).pack(fill="x", padx=28, pady=(10, 0))

        self.run_button = tk.Button(
            sidebar, text="WAITING FOR BOARD", command=self._start_test, state="disabled",
            bg="#315796", activebackground="#20BA62", disabledforeground="#9DB3D8",
            fg="white", font=("Segoe UI Semibold", 13),
            relief="flat", padx=18, pady=16, cursor="hand2", bd=0,
        )
        self.run_button.pack(side="bottom", fill="x", padx=24, pady=24)
        tk.Label(sidebar, text="LORDOFROBOTS.COM", bg=BRAND_BLUE, fg="#7496CF", font=("Segoe UI Semibold", 8)).pack(side="bottom", pady=(0, 2))

        main = tk.Frame(self.root, bg=APP_BACKGROUND, padx=30, pady=24)
        main.grid(row=0, column=1, sticky="nsew")

        header = tk.Frame(main, bg=APP_BACKGROUND)
        header.pack(fill="x", pady=(0, 18))
        title_group = tk.Frame(header, bg=APP_BACKGROUND)
        title_group.pack(side="left")
        tk.Label(title_group, text="LOR CORE V3", bg=APP_BACKGROUND, fg=BRAND_BLUE, font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(title_group, text="Production Test", bg=APP_BACKGROUND, fg=TEXT_PRIMARY, font=("Segoe UI Semibold", 27)).pack(anchor="w", pady=(1, 0))
        tk.Label(title_group, text="Fast, repeatable end-of-line verification", bg=APP_BACKGROUND, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        self.summary_label = tk.Label(
            header, text="STANDBY", bg="#E8EDF4", fg=TEXT_MUTED,
            font=("Segoe UI Semibold", 10), padx=18, pady=9,
        )
        self.summary_label.pack(side="right", anchor="n", pady=8)

        self.notebook = ttk.Notebook(main, style="Modern.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        live_tab = tk.Frame(self.notebook, bg=APP_BACKGROUND)
        history_tab = tk.Frame(self.notebook, bg=SURFACE)
        self.notebook.add(live_tab, text="LIVE TEST")
        self.notebook.add(history_tab, text="TEST HISTORY")

        settings = tk.Frame(live_tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=15)
        self.settings_card = settings
        settings.pack(fill="x", pady=(0, 12))
        settings_header = tk.Frame(settings, bg=SURFACE)
        settings_header.pack(fill="x", pady=(0, 10))
        tk.Label(settings_header, text="Test setup", bg=SURFACE, fg=TEXT_PRIMARY, font=("Segoe UI Semibold", 12)).pack(side="left")
        self.advanced_button = tk.Button(
            settings_header, text="TEST PARAMETERS  +", command=self._toggle_advanced,
            bg=SURFACE, activebackground=SURFACE, fg=BRAND_BLUE, activeforeground=BRAND_BLUE_LIGHT,
            font=("Segoe UI Semibold", 9), relief="flat", bd=0, cursor="hand2",
        )
        self.advanced_button.pack(side="right")

        basics = tk.Frame(settings, bg=SURFACE)
        basics.pack(fill="x")
        for column in range(3):
            basics.grid_columnconfigure(column, weight=1, uniform="basic")

        def add_field(parent, column: int, label: str, variable: tk.StringVar, combo: bool = False):
            field = tk.Frame(parent, bg=SURFACE)
            field.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0 if column == 2 else 8))
            tk.Label(field, text=label.upper(), bg=SURFACE, fg=TEXT_MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 5))
            if combo:
                widget = ttk.Combobox(field, textvariable=variable, state="readonly", style="Modern.TCombobox")
            else:
                widget = ttk.Entry(field, textvariable=variable, style="Modern.TEntry")
            widget.pack(fill="x")
            return widget

        self.port_combo = add_field(basics, 0, "Detected port", self.port_var, combo=True)
        add_field(basics, 1, "Board serial (optional)", self.serial_var)
        add_field(basics, 2, "Operator", self.operator_var)

        self.advanced_frame = tk.Frame(settings, bg=SURFACE)
        for column in range(4):
            self.advanced_frame.grid_columnconfigure(column, weight=1, uniform="advanced")

        advanced_fields = [
            ("Fixture VIN", self.vin_var), ("VIN tolerance", self.tolerance_var),
            ("Factory Wi-Fi SSID", self.ssid_var), ("Minimum RSSI (dBm)", self.rssi_var),
        ]
        for column, (label, variable) in enumerate(advanced_fields):
            field = tk.Frame(self.advanced_frame, bg=SURFACE)
            field.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 7, 0 if column == 3 else 7))
            tk.Label(field, text=label.upper(), bg=SURFACE, fg=TEXT_MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 5))
            ttk.Entry(field, textvariable=variable, style="Modern.TEntry").pack(fill="x")

        status_card = tk.Frame(
            live_tab, bg="#EDF4FF", highlightbackground="#B8CBEB",
            highlightthickness=2, padx=18, pady=13,
        )
        self.status_card = status_card
        status_card.pack(fill="x", pady=(0, 12))
        self.status_top = tk.Frame(status_card, bg="#EDF4FF")
        status_top = self.status_top
        status_top.pack(fill="x")
        self.action_kicker = tk.Label(
            status_top, text="CURRENT STEP", bg="#EDF4FF", fg=BRAND_BLUE,
            font=("Segoe UI Semibold", 8), anchor="w",
        )
        self.action_kicker.pack(anchor="w")
        self.phase_label = tk.Label(
            status_top, text="Connect a board to begin.", bg="#EDF4FF", fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14), anchor="w", justify="left", wraplength=650,
        )
        self.phase_label.pack(anchor="w", fill="x", expand=True, pady=(2, 0))
        self.led_pass = tk.Button(
            status_top, text="LEDS LOOK GOOD", command=lambda: self._answer_led(True),
            bg=SUCCESS, activebackground="#20BA62", fg="white", font=("Segoe UI Semibold", 9),
            relief="flat", padx=13, pady=7, bd=0, cursor="hand2",
        )
        self.led_fail = tk.Button(
            status_top, text="LED FAILURE", command=lambda: self._answer_led(False),
            bg=FAILURE, activebackground="#EF5A5A", fg="white", font=("Segoe UI Semibold", 9),
            relief="flat", padx=13, pady=7, bd=0, cursor="hand2",
        )

        self.progress_host = tk.Frame(status_card, bg="#EDF4FF")
        self.progress_host.pack(fill="x", pady=(10, 0))
        self.progress_bar = ttk.Progressbar(
            self.progress_host, mode="indeterminate", maximum=100,
            style="Factory.Horizontal.TProgressbar",
        )

        results_card = tk.Frame(live_tab, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        results_card.pack(fill="both", expand=True)
        results_header = tk.Frame(results_card, bg=SURFACE, padx=18, pady=13)
        results_header.pack(fill="x")
        tk.Label(results_header, text="Test results", bg=SURFACE, fg=TEXT_PRIMARY, font=("Segoe UI Semibold", 12)).pack(side="left")
        tk.Label(results_header, text="LIVE", bg="#E7F0FF", fg=BRAND_BLUE, font=("Segoe UI Semibold", 8), padx=9, pady=4).pack(side="right")

        table = tk.Frame(results_card, bg=SURFACE)
        table.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.tree = ttk.Treeview(table, columns=("test", "result", "details"), show="headings", height=10)
        self.tree.heading("test", text="Test")
        self.tree.heading("result", text="Result")
        self.tree.heading("details", text="Details")
        self.tree.column("test", width=190, anchor="w")
        self.tree.column("result", width=90, anchor="center")
        self.tree.column("details", width=700, anchor="w")
        self.tree.tag_configure("pass", foreground=SUCCESS)
        self.tree.tag_configure("fail", foreground=FAILURE)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        history_header = tk.Frame(history_tab, bg=SURFACE, padx=18, pady=6)
        history_header.pack(fill="x")
        tk.Label(history_header, text="Board test history", bg=SURFACE, fg=TEXT_PRIMARY, font=("Segoe UI Semibold", 12)).pack(side="left")
        tk.Button(
            history_header, text="REFRESH", command=self._load_history, bg=SURFACE,
            activebackground="#EEF3FA", fg=BRAND_BLUE, activeforeground=BRAND_BLUE_LIGHT,
            font=("Segoe UI Semibold", 9), relief="flat", bd=0, cursor="hand2", padx=10,
        ).pack(side="right")

        history_filters = tk.Frame(history_tab, bg="#F7F9FC", padx=18, pady=5)
        history_filters.pack(fill="x")
        self.history_search_var = tk.StringVar()
        self.history_filter_var = tk.StringVar(value="ALL RESULTS")
        tk.Label(history_filters, text="SEARCH", bg="#F7F9FC", fg=TEXT_MUTED, font=("Segoe UI Semibold", 8)).pack(side="left", padx=(0, 7))
        history_search = ttk.Entry(history_filters, textvariable=self.history_search_var, style="Modern.TEntry", width=28)
        history_search.pack(side="left", padx=(0, 18))
        history_search.bind("<KeyRelease>", lambda _event: self._load_history())
        history_filter = ttk.Combobox(
            history_filters, textvariable=self.history_filter_var,
            values=("ALL RESULTS", "PASS", "FAIL"), state="readonly", style="Modern.TCombobox", width=14,
        )
        history_filter.pack(side="left")
        history_filter.bind("<<ComboboxSelected>>", lambda _event: self._load_history())
        self.history_count_label = tk.Label(history_filters, text="0 records", bg="#F7F9FC", fg=TEXT_MUTED, font=("Segoe UI", 9))
        self.history_count_label.pack(side="right")

        self.history_records: dict[str, dict] = {}

        history_body = tk.Frame(history_tab, bg=APP_BACKGROUND, padx=8, pady=7)
        history_body.pack(fill="both", expand=True)
        history_body.grid_rowconfigure(0, weight=1)
        history_body.grid_columnconfigure(0, weight=5, minsize=330)
        history_body.grid_columnconfigure(1, weight=7, minsize=440)

        history_list_panel = tk.Frame(
            history_body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1,
        )
        history_list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(
            history_list_panel, text="TEST RUNS", bg=SURFACE, fg=TEXT_MUTED,
            font=("Segoe UI Semibold", 8), padx=14, pady=11,
        ).pack(fill="x", anchor="w")

        history_table = tk.Frame(history_list_panel, bg=SURFACE)
        history_table.pack(fill="both", expand=True)
        history_columns = ("timestamp", "board", "result")
        self.history_tree = ttk.Treeview(history_table, columns=history_columns, show="headings", height=8)
        headings = {
            "timestamp": ("Date / Time", 112), "board": ("Board ID / Serial", 134),
            "result": ("Result", 48),
        }
        for column, (heading, width) in headings.items():
            self.history_tree.heading(column, text=heading)
            self.history_tree.column(column, width=width, anchor="w" if column != "result" else "center")
        self.history_tree.tag_configure("pass", foreground=SUCCESS)
        self.history_tree.tag_configure("fail", foreground=FAILURE)
        history_scrollbar = ttk.Scrollbar(history_table, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        history_scrollbar.pack(side="right", fill="y")
        self.history_tree.pack(side="left", fill="both", expand=True)
        self.history_tree.bind("<<TreeviewSelect>>", self._show_history_details)

        detail_panel = tk.Frame(
            history_body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1,
            padx=14, pady=9,
        )
        detail_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        detail_heading = tk.Frame(detail_panel, bg=SURFACE)
        detail_heading.pack(fill="x")
        detail_titles = tk.Frame(detail_heading, bg=SURFACE)
        detail_titles.pack(side="left", fill="x", expand=True)
        tk.Label(
            detail_titles, text="SELECTED BOARD", bg=SURFACE, fg=TEXT_MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w")
        self.history_selected_title = tk.Label(
            detail_titles, text="Select a test run", bg=SURFACE, fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14), anchor="w",
        )
        self.history_selected_title.pack(anchor="w", pady=(1, 0))
        self.history_selected_meta = tk.Label(
            detail_titles, text="Test data will appear here", bg=SURFACE, fg=TEXT_MUTED,
            font=("Segoe UI", 8), anchor="w",
        )
        self.history_selected_meta.pack(anchor="w", pady=(2, 0))
        self.history_result_badge = tk.Label(
            detail_heading, text="—", bg="#E8EDF4", fg=TEXT_MUTED,
            font=("Segoe UI Semibold", 10), padx=14, pady=7,
        )
        self.history_result_badge.pack(side="right", anchor="n")

        metrics = tk.Frame(detail_panel, bg=SURFACE)
        metrics.pack(fill="x", pady=(8, 7))
        self.history_metric_values: dict[str, tk.Label] = {}
        self.history_metric_notes: dict[str, tk.Label] = {}
        for column, (key, title) in enumerate((("vin", "BATTERY"), ("wifi", "WI-FI"), ("bluetooth", "BLUETOOTH"))):
            metrics.grid_columnconfigure(column, weight=1, uniform="metric")
            card = tk.Frame(metrics, bg="#F5F8FC", padx=9, pady=5)
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0 if column == 2 else 4))
            tk.Label(card, text=title, bg="#F5F8FC", fg=TEXT_MUTED, font=("Segoe UI Semibold", 7)).pack(anchor="w")
            value = tk.Label(card, text="—", bg="#F5F8FC", fg=TEXT_PRIMARY, font=("Segoe UI Semibold", 11))
            value.pack(anchor="w", pady=(2, 0))
            note = tk.Label(card, text="No data", bg="#F5F8FC", fg=TEXT_MUTED, font=("Segoe UI", 8))
            note.pack(anchor="w")
            self.history_metric_values[key] = value
            self.history_metric_notes[key] = note

        tk.Label(
            detail_panel, text="TEST DATA", bg=SURFACE, fg=TEXT_MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w", pady=(0, 3))
        detail_table = tk.Frame(detail_panel, bg=SURFACE)
        detail_table.pack(fill="both", expand=True)
        self.history_detail_tree = ttk.Treeview(
            detail_table, columns=("test", "result", "data"), show="headings", height=7,
        )
        self.history_detail_tree.heading("test", text="Check")
        self.history_detail_tree.heading("result", text="Status")
        self.history_detail_tree.heading("data", text="Measurement / Details")
        self.history_detail_tree.column("test", width=125, anchor="w")
        self.history_detail_tree.column("result", width=62, anchor="center")
        self.history_detail_tree.column("data", width=300, anchor="w")
        self.history_detail_tree.tag_configure("pass", foreground=SUCCESS)
        self.history_detail_tree.tag_configure("fail", foreground=FAILURE)
        detail_scrollbar = ttk.Scrollbar(detail_table, orient="vertical", command=self.history_detail_tree.yview)
        self.history_detail_tree.configure(yscrollcommand=detail_scrollbar.set)
        detail_scrollbar.pack(side="right", fill="y")
        self.history_detail_tree.pack(side="left", fill="both", expand=True)

        tk.Label(
            main, text=f"Results append automatically  •  {CSV_FILE}", bg=APP_BACKGROUND,
            fg="#8A98AA", font=("Segoe UI", 8), anchor="w",
        ).pack(fill="x", pady=(9, 0))
        self._load_history()

    def _poll_ports(self) -> None:
        if not self.running:
            candidates = list_candidate_ports()
            ports = tuple(port for port, _ in candidates)
            self.port_descriptions = dict(candidates)
            if ports != self.last_ports:
                self.last_ports = ports
                self.port_combo["values"] = ports
                if ports and self.port_var.get() not in ports:
                    self.port_var.set(ports[0])
                if not ports:
                    self.port_var.set("")
                self._update_connection_state()
        self.root.after(1000, self._poll_ports)

    def _animate_brand_logo(self) -> None:
        if self.logo_image is None or not BRAND_GIF.exists():
            return
        try:
            self.logo_frame_index = (self.logo_frame_index + 1) % 213
            frame = tk.PhotoImage(file=str(BRAND_GIF), format=f"gif -index {self.logo_frame_index}")
            self.logo_image = frame
            self.logo_label.configure(image=frame)
        except tk.TclError:
            self.logo_frame_index = 0
        self.root.after(45, self._animate_brand_logo)

    def _toggle_advanced(self) -> None:
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.pack(fill="x", pady=(14, 0))
            self.advanced_button.configure(text="TEST PARAMETERS  −")
        else:
            self.advanced_frame.pack_forget()
            self.advanced_button.configure(text="TEST PARAMETERS  +")

    def _load_history(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self.history_records.clear()

        search = self.history_search_var.get().strip().lower()
        result_filter = self.history_filter_var.get()
        records: list[dict] = []
        if CSV_FILE.exists():
            try:
                with CSV_FILE.open("r", newline="", encoding="utf-8") as stream:
                    records = list(csv.DictReader(stream))
            except (OSError, csv.Error):
                records = []

        visible_count = 0
        first_iid: str | None = None
        for record in reversed(records):
            overall = "PASS" if record.get("overall_pass", "").lower() == "true" else "FAIL"
            if result_filter != "ALL RESULTS" and overall != result_filter:
                continue
            formatted_board_id = canonical_board_id(record.get("board_id", ""))
            searchable = " ".join(
                record.get(field, "") for field in
                ("timestamp_utc", "serial_label", "board_id", "operator", "com_port", "firmware")
            ).lower() + " " + formatted_board_id.lower()
            if search and search not in searchable:
                continue

            timestamp = record.get("timestamp_utc", "")
            try:
                timestamp = datetime.fromisoformat(timestamp).astimezone().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass
            board = record.get("serial_label") or formatted_board_id or "Unknown"
            iid = self.history_tree.insert(
                "", "end",
                values=(timestamp, board, overall),
                tags=(overall.lower(),),
            )
            if first_iid is None:
                first_iid = iid
            self.history_records[iid] = record
            visible_count += 1
        self.history_count_label.configure(text=f"{visible_count} record{'s' if visible_count != 1 else ''}")
        if first_iid is not None:
            self.history_tree.selection_set(first_iid)
            self.history_tree.focus(first_iid)
            self._show_history_details()
        else:
            self._clear_history_details()

    def _clear_history_details(self) -> None:
        self.history_selected_title.configure(text="Select a test run")
        self.history_selected_meta.configure(text="Test data will appear here")
        self.history_result_badge.configure(text="—", bg="#E8EDF4", fg=TEXT_MUTED)
        for key in self.history_metric_values:
            self.history_metric_values[key].configure(text="—", fg=TEXT_PRIMARY)
            self.history_metric_notes[key].configure(text="No data")
        for item in self.history_detail_tree.get_children():
            self.history_detail_tree.delete(item)

    def _show_history_details(self, _event=None) -> None:
        selection = self.history_tree.selection()
        if not selection:
            return
        record = self.history_records.get(selection[0], {})
        formatted_board_id = canonical_board_id(record.get("board_id", ""))
        board_name = record.get("serial_label") or formatted_board_id or "Unknown board"
        self.history_selected_title.configure(text=board_name)

        timestamp = record.get("timestamp_utc", "")
        try:
            timestamp = datetime.fromisoformat(timestamp).astimezone().strftime("%b %d, %Y  %I:%M %p")
        except ValueError:
            pass
        metadata = [timestamp, record.get("com_port", ""), record.get("firmware", "")]
        if record.get("serial_label") and formatted_board_id:
            metadata.insert(0, formatted_board_id)
        if record.get("operator"):
            metadata.append(f"Operator {record['operator']}")
        self.history_selected_meta.configure(text="  •  ".join(item for item in metadata if item))

        overall = record.get("overall_pass", "").lower() == "true"
        self.history_result_badge.configure(
            text="PASS" if overall else "FAIL",
            bg="#DCF6E7" if overall else "#FDE4E4",
            fg="#0B7438" if overall else "#A22626",
        )

        for item in self.history_detail_tree.get_children():
            self.history_detail_tree.delete(item)
        tests: list[dict] = []
        try:
            tests = json.loads(record.get("details_json", "[]"))
            for test in tests:
                outcome = "PASS" if test.get("pass") else "FAIL"
                details = test.get("details", "")
                if test.get("test") == "Board identity" and record.get("board_id"):
                    details = details.replace(record["board_id"], formatted_board_id)
                details = format_test_details(test.get("test", ""), details)
                self.history_detail_tree.insert(
                    "", "end", values=(test.get("test", ""), outcome, details),
                    tags=(outcome.lower(),),
                )
        except (json.JSONDecodeError, TypeError):
            self.history_detail_tree.insert(
                "", "end", values=("Stored data", "—", record.get("details_json", "")),
            )

        tests_by_name = {test.get("test"): test for test in tests}

        def update_metric(key: str, value: str, note: str, passed: bool | None) -> None:
            color = TEXT_PRIMARY if passed is None else (SUCCESS if passed else FAILURE)
            self.history_metric_values[key].configure(text=value or "—", fg=color)
            self.history_metric_notes[key].configure(text=note or "No data")

        vin_test = tests_by_name.get("Battery voltage", {})
        vin_details = parse_details(vin_test.get("details", ""))
        vin_value = record.get("vin_volts", "")
        vin_note = ""
        if vin_details.get("min") and vin_details.get("max"):
            vin_note = f"Range {vin_details['min']}–{vin_details['max']} V"
        if vin_details.get("raw_adc"):
            vin_note = f"Raw ADC {vin_details['raw_adc']} avg • {vin_note}".rstrip(" •")
        update_metric(
            "vin", f"{vin_value} V" if vin_value else "—", vin_note,
            record.get("vin_pass", "").lower() == "true" if vin_value else None,
        )

        wifi_value = record.get("wifi_rssi_dbm", "")
        wifi_note_parts = []
        if record.get("wifi_networks"):
            wifi_note_parts.append(f"{record['wifi_networks']} networks")
        if record.get("wifi_target"):
            wifi_note_parts.append(record["wifi_target"])
        update_metric(
            "wifi", f"{wifi_value} dBm" if wifi_value else "—", " • ".join(wifi_note_parts),
            record.get("wifi_pass", "").lower() == "true" if wifi_value else None,
        )

        bt_test = tests_by_name.get("Bluetooth", {}) or tests_by_name.get("BLUETOOTH", {})
        bt_details = parse_details(bt_test.get("details", ""))
        bt_rssi = bt_details.get("best_rssi_dbm", "")
        bt_note = f"{bt_details['devices']} devices" if bt_details.get("devices") else "Radio check"
        update_metric(
            "bluetooth", f"{bt_rssi} dBm" if bt_rssi else ("PASS" if record.get("bluetooth_pass", "").lower() == "true" else "FAIL"),
            bt_note, record.get("bluetooth_pass", "").lower() == "true",
        )

    def _set_instruction(self, text: str, waiting_for_operator: bool = False) -> None:
        if waiting_for_operator:
            background, border = "#FFF3D6", "#F0B64C"
            kicker_text, kicker_color, message_color = "OPERATOR ACTION REQUIRED", "#A25B00", "#583900"
        else:
            background, border = "#EDF4FF", "#B8CBEB"
            kicker_text, kicker_color, message_color = "CURRENT STEP", BRAND_BLUE, TEXT_PRIMARY
        self.status_card.configure(bg=background, highlightbackground=border)
        self.status_top.configure(bg=background)
        self.progress_host.configure(bg=background)
        self.action_kicker.configure(text=kicker_text, bg=background, fg=kicker_color)
        self.phase_label.configure(text=text, bg=background, fg=message_color)

    def _update_connection_state(self) -> None:
        port = self.port_var.get()
        if port:
            description = self.port_descriptions.get(port, "USB serial device")
            self.connection_label.configure(
                text=f"●  BOARD CONNECTED\n    {port}  •  {description}", fg="#74E49D",
            )
            self.run_button.configure(state="normal", text="RUN PRODUCTION TEST", bg=SUCCESS)
            self._set_instruction("Board detected. Press RUN PRODUCTION TEST when ready.")
        else:
            self.connection_label.configure(text="○  WAITING FOR BOARD", fg="#BED0EF")
            self.run_button.configure(state="disabled", text="WAITING FOR BOARD", bg="#315796")
            self._set_instruction("Connect a LoR Core over USB-C to begin.")

    def _start_test(self) -> None:
        try:
            settings = {
                "port": self.port_var.get(),
                "serial_label": self.serial_var.get().strip(),
                "operator": self.operator_var.get().strip(),
                "vin": float(self.vin_var.get()),
                "tolerance": float(self.tolerance_var.get()),
                "ssid": self.ssid_var.get().strip(),
                "min_rssi": int(self.rssi_var.get()),
                "mapping": CONTROL_MAPPING_NAME,
            }
            if not settings["port"]:
                raise ValueError("No serial port is selected")
            if settings["tolerance"] <= 0:
                raise ValueError("VIN tolerance must be greater than zero")
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return

        self.running = True
        self.notebook.select(0)
        self.run_button.configure(state="disabled", text="TEST IN PROGRESS", bg="#315796")
        self.summary_label.configure(text="TESTING", bg="#E7F0FF", fg=BRAND_BLUE)
        self._set_instruction("Preparing the board for production testing...")
        self.led_pass.pack_forget()
        self.led_fail.pack_forget()
        for item in self.tree.get_children():
            self.tree.delete(item)
        threading.Thread(target=self._run_test, args=(settings,), daemon=True).start()

    def _emit(self, *event) -> None:
        self.events.put(event)

    def _run_tool(self, command: list[str], phase: str, timeout: int, track_progress: bool = False) -> None:
        self._emit("activity_start", phase, track_progress)
        process: subprocess.Popen | None = None
        output_lines: list[str] = []
        try:
            process = subprocess.Popen(
                command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            line_queue: queue.Queue[str | None] = queue.Queue()

            def collect_output() -> None:
                assert process is not None and process.stdout is not None
                for line in process.stdout:
                    line_queue.put(line)
                line_queue.put(None)

            threading.Thread(target=collect_output, daemon=True).start()
            deadline = time.monotonic() + timeout
            output_complete = False
            primary_flash_started = False
            while not output_complete:
                if time.monotonic() >= deadline:
                    process.kill()
                    raise TimeoutError(f"{phase} timed out after {timeout} seconds")
                try:
                    line = line_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if line is None:
                    output_complete = True
                    continue
                output_lines.append(line)
                if "Flash will be erased from 0x00010000" in line:
                    primary_flash_started = True
                if track_progress:
                    percentages = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%", line)
                    if percentages and primary_flash_started:
                        self._emit("progress", min(100, int(float(percentages[-1]))))

            return_code = process.wait(timeout=max(1, int(deadline - time.monotonic())))
            if track_progress and return_code == 0:
                self._emit("progress", 100)
            if return_code:
                output = "".join(output_lines).strip()
                raise RuntimeError(f"{phase} failed:\n{output[-3500:]}")
        finally:
            self._emit("activity_stop")

    def _run_test(self, settings: dict) -> None:
        rows: list[dict] = []
        record = {field: "" for field in CSV_FIELDS}
        record.update({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "operator": settings["operator"], "serial_label": settings["serial_label"],
            "com_port": settings["port"], "control_mapping": settings["mapping"],
        })
        dut: Dut | None = None
        try:
            cli = find_arduino_cli()
            BUILD.mkdir(parents=True, exist_ok=True)
            if firmware_needs_compile():
                self._run_tool(
                    [cli, "compile", "--fqbn", FQBN, "--board-options", "PartitionScheme=huge_app",
                     str(SKETCH), "--build-path", str(BUILD)],
                    "Compiling specialized test firmware (first run may take several minutes)...", 420,
                )
            else:
                self._emit("phase", "Using the verified cached test firmware...")
            self._run_tool(
                [cli, "upload", "--fqbn", FQBN, "--board-options", "PartitionScheme=huge_app",
                 "--port", settings["port"], str(SKETCH), "--build-path", str(BUILD)],
                "Uploading test firmware to the detected board...", 120, track_progress=True,
            )
            self._emit("phase", "Connecting to LoR Core test firmware...")
            dut = Dut(settings["port"])

            info = dut.command("INFO", lambda m: m.get("type") == "info", 8)
            if info.get("product") != "LoR Core V3":
                raise RuntimeError("The programmed device did not return the LoR Core V3 handshake")
            record.update({
                "board_id": info.get("mac", ""), "firmware": info.get("firmware", ""),
                "chip": info.get("chip", ""), "chip_revision": info.get("revision", ""),
                "flash_bytes": info.get("flash_bytes", ""),
            })
            self._add_result(rows, "Board identity", True, f"ID {record['board_id']} / {record['firmware']}")
            dut.command("TEST_START", lambda m: m.get("test") == "TEST_START", 5)

            self._emit("phase", "Reading battery/input voltage...")
            low = settings["vin"] - settings["tolerance"]
            high = settings["vin"] + settings["tolerance"]
            vin = dut.command(f"VIN {low:.3f} {high:.3f}", lambda m: m.get("test") == "VIN", 8)
            vin_details = parse_details(vin.get("details", ""))
            record["vin_volts"] = vin_details.get("volts", "")
            record["vin_pass"] = vin.get("pass", False)
            self._add_result(rows, "Battery voltage", bool(vin.get("pass")), vin.get("details", ""))

            self._emit("phase", "Scanning Wi-Fi and measuring RSSI...")
            wifi_command = f"WIFI {settings['ssid']} {settings['min_rssi']}" if settings["ssid"] else f"WIFI {settings['min_rssi']}"
            wifi = dut.command(wifi_command, lambda m: m.get("test") == "WIFI", 25)
            wifi_details = parse_details(wifi.get("details", ""))
            record.update({
                "wifi_pass": wifi.get("pass", False), "wifi_networks": wifi_details.get("networks", ""),
                "wifi_target": wifi_details.get("target", ""), "wifi_rssi_dbm": wifi_details.get("rssi_dbm", ""),
            })
            self._add_result(rows, "Wi-Fi / RSSI", bool(wifi.get("pass")), wifi.get("details", ""))

            self._emit("phase", "Checking Bluetooth controller...")
            bluetooth = dut.command("BT", lambda m: m.get("test") == "BLUETOOTH", 10)
            record["bluetooth_pass"] = bluetooth.get("pass", False)
            self._add_result(rows, "Bluetooth", bool(bluetooth.get("pass")), bluetooth.get("details", ""))

            dut.command("LED_DEMO", lambda m: m.get("test") == "LED_DEMO", 8)
            self.led_answer = None
            self.led_event.clear()
            self._emit(
                "phase",
                "CHECK THE FOUR LEDS — confirm the rainbow wash and icy-blue comet animation.",
                True,
            )
            self._emit("led_prompt")
            if not self.led_event.wait(120):
                led_ok = False
                led_detail = "operator confirmation timed out"
            else:
                led_ok = bool(self.led_answer)
                led_detail = "operator confirmed animation" if led_ok else "operator rejected animation"
            record["led_pass"] = led_ok
            self._add_result(rows, "Four RGB LEDs", led_ok, led_detail)

            mapping = CONTROL_MAPPING
            control_prompts = {
                "BTN_A": "PRESS AND HOLD BUTTON A — the LEDs should turn YELLOW.",
                "BTN_B": "PRESS AND HOLD BUTTON B — the LEDs should turn GREEN.",
                "BTN_C": "PRESS AND HOLD BUTTON C — the LEDs should turn RED.",
                "BTN_D": "PRESS AND HOLD BUTTON D — the LEDs should turn BLUE.",
                "SW": "TOGGLE THE USER SWITCH to its other position.",
            }
            for control in ("BTN_A", "BTN_B", "BTN_C", "BTN_D", "SW"):
                self._emit("phase", control_prompts[control], True)
                baseline = dut.inputs()
                expected_pin = mapping[control]
                changed: list[int] = []
                deadline = time.monotonic() + 18
                while time.monotonic() < deadline:
                    current = dut.inputs()
                    changed = [pin for pin in baseline if current[pin] != baseline[pin]]
                    if expected_pin in changed:
                        break
                    time.sleep(0.08)
                passed = changed == [expected_pin]
                detail = f"expected GPIO{expected_pin}; changed {changed or 'none'}"
                record[("switch" if control == "SW" else control.lower()) + "_pass"] = passed
                self._add_result(rows, control.replace("_", " "), passed, detail)
                if control != "SW" and passed:
                    self._emit("phase", f"RELEASE {control.replace('_', ' ')}.", True)
                    release_deadline = time.monotonic() + 8
                    while time.monotonic() < release_deadline and dut.inputs()[expected_pin] != baseline[expected_pin]:
                        time.sleep(0.08)

            pass_fields = [
                "vin_pass", "wifi_pass", "bluetooth_pass", "btn_a_pass", "btn_b_pass",
                "btn_c_pass", "btn_d_pass", "switch_pass", "led_pass",
            ]
            overall = all(record.get(field) is True for field in pass_fields)
            record["overall_pass"] = overall
            if overall:
                self._emit("phase", "PASS - showing green for two seconds, then returning to icy-blue breathing.")
                dut.command("TEST_PASS", lambda m: m.get("test") == "TEST_PASS", 6)
            else:
                self._emit("phase", "FAIL - locking the board LEDs red.")
                dut.command("TEST_FAIL", lambda m: m.get("test") == "TEST_FAIL", 5)
            record["details_json"] = json.dumps(rows, separators=(",", ":"))
            self._append_csv(record)
            self._emit("complete", overall, record["board_id"], str(CSV_FILE))
        except Exception as exc:
            if dut is not None:
                try:
                    dut.command("TEST_FAIL", lambda m: m.get("test") == "TEST_FAIL", 5)
                except Exception:
                    pass
            record["overall_pass"] = False
            rows.append({"test": "Station error", "pass": False, "details": str(exc)})
            record["details_json"] = json.dumps(rows, separators=(",", ":"))
            try:
                self._append_csv(record)
            except Exception:
                pass
            self._emit("error", str(exc))
        finally:
            if dut is not None:
                dut.close()

    def _add_result(self, rows: list[dict], name: str, passed: bool, details: str) -> None:
        row = {"test": name, "pass": passed, "details": details}
        rows.append(row)
        self._emit("row", row)

    @staticmethod
    def _append_csv(record: dict) -> None:
        CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0
        with CSV_FILE.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
            if needs_header:
                writer.writeheader()
            writer.writerow(record)

    def _answer_led(self, passed: bool) -> None:
        self.led_answer = passed
        self.led_event.set()
        self.led_pass.pack_forget()
        self.led_fail.pack_forget()

    def _show_activity(self, text: str, determinate: bool = False) -> None:
        self.activity_token += 1
        token = self.activity_token
        self.activity_text = text.rstrip(" .")
        self.activity_percent = 0 if determinate else None
        self._set_instruction(text)
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate" if determinate else "indeterminate", value=0)
        self.progress_bar.pack(fill="x")
        if not determinate:
            self.progress_bar.start(10)
        self._animate_activity(token, 0)

    def _animate_activity(self, token: int, frame: int) -> None:
        if token != self.activity_token:
            return
        spinner = ("|", "/", "-", "\\")[frame % 4]
        if self.activity_percent is None:
            dots = "." * ((frame % 3) + 1)
            label = f"{self.activity_text}{dots}  {spinner}"
        else:
            label = f"{self.activity_text}  {self.activity_percent}%  {spinner}"
        self.phase_label.configure(text=label)
        self.root.after(180, self._animate_activity, token, frame + 1)

    def _set_activity_progress(self, value: int) -> None:
        self.activity_percent = max(0, min(100, value))
        self.progress_bar.configure(value=self.activity_percent)

    def _hide_activity(self) -> None:
        self.activity_token += 1
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "phase":
                    self._set_instruction(event[1], bool(event[2]) if len(event) > 2 else False)
                elif kind == "activity_start":
                    self._show_activity(event[1], event[2])
                elif kind == "progress":
                    self._set_activity_progress(event[1])
                elif kind == "activity_stop":
                    self._hide_activity()
                elif kind == "row":
                    row = event[1]
                    passed = row["pass"]
                    self.tree.insert("", "end", values=(row["test"], "PASS" if passed else "FAIL", row["details"]), tags=("pass" if passed else "fail",))
                    self.tree.yview_moveto(1)
                elif kind == "led_prompt":
                    self.led_pass.pack(side="left", padx=(10, 4))
                    self.led_fail.pack(side="left", padx=4)
                elif kind == "complete":
                    self._hide_activity()
                    overall, board_id, csv_path = event[1:]
                    self.running = False
                    if overall:
                        self.summary_label.configure(text="PASS", fg="#0B7438", bg="#DCF6E7")
                    else:
                        self.summary_label.configure(text="FAIL", fg="#A22626", bg="#FDE4E4")
                    self._update_connection_state()
                    self._set_instruction(f"Test complete • Board {board_id} • CSV record saved")
                    self._load_history()
                elif kind == "error":
                    self._hide_activity()
                    self.running = False
                    self.summary_label.configure(text="ERROR", fg="#A22626", bg="#FDE4E4")
                    self._update_connection_state()
                    self._set_instruction("Test stopped • Failure recorded when possible")
                    self.phase_label.configure(fg=FAILURE)
                    self._load_history()
                    messagebox.showerror("Production test stopped", event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)


def main() -> None:
    root = tk.Tk()
    TestStation(root)
    root.mainloop()


if __name__ == "__main__":
    main()
