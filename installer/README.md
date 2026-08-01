# Windows Installer

`build-installer.ps1` creates a self-contained, machine-wide Windows installer for the LoR Core V3 Production Test Station.

## Operator package contents

The generated setup program contains:

- the Tkinter UI frozen as a Windows executable;
- the Python runtime and pyserial;
- a standalone esptool uploader;
- the four verified ESP32 flash images for `production-test-1.14`;
- all Lord of Robots image, GIF, and icon assets;
- desktop and Start Menu shortcuts;
- Windows uninstall registration.

Python, Arduino IDE, the ESP32 Arduino core, and FastLED are not required on an operator PC. Only the WCH CH340/CH341 USB-serial driver may be needed if Windows does not automatically recognize the LoR Core.

## Build prerequisites

The release-builder PC requires:

- Windows 10 or 11;
- Python 3 with `pyinstaller`, `esptool`, and `pyserial`;
- Arduino IDE 2.x in its standard installation directory;
- Espressif's ESP32 Arduino core and FastLED;
- Inno Setup 6, with a commercial license activated when the package is built for commercial use.

Install the Python packaging tools with:

```powershell
py -3 -m pip install --user pyinstaller esptool pyserial
```

Install Inno Setup with:

```powershell
winget install --id JRSoftware.InnoSetup --exact
```

## Build

From the repository root, run:

```powershell
.\installer\build-installer.ps1
```

The script performs a clean release build:

1. compiles the production firmware with the `huge_app` partition scheme;
2. creates a versioned firmware ZIP and SHA-256 manifest;
3. builds a standalone esptool uploader;
4. freezes the UI and embeds the branding, updater, and verified fallback firmware;
5. compiles the Inno Setup package;
6. creates the update manifest and collects the three GitHub Release assets.

The output is:

```text
installer\output\LoR_Core_V3_Test_Station_Setup_1.14.0.exe
```

Ready-to-publish assets are collected in:

```text
installer\output\release
```

## Publish an update

Create a normal, published GitHub Release in `LordofRobots/TestRig_LoR_Core_V3` and attach all three files from `installer\output\release`:

```text
LoR_Core_V3_Test_Station_Setup_1.14.0.exe
lor-core-v3-firmware-production-test-1.14.zip
lor-core-v3-update-manifest.json
```

Do not rename the assets after building them. The update manifest contains the exact asset names and SHA-256 checksums. Draft and prerelease releases are intentionally ignored by production stations. A release may update the app, firmware, or both; version comparison prevents unnecessary downloads.

The application uses the public GitHub Releases API, so update checks for this public repository do not require credentials. There is no resident update service: one daemon thread checks shortly after launch and exits. Firmware is approximately 1 MB and is downloaded only when newer. The full installer is downloaded only for a newer application version.

Before publishing, validate the generated updater deterministically:

```powershell
py -3 .\installer\test_update_manager.py
```

The test verifies successful app and firmware activation, all hashes, the approved flash-image set, and rollback to the prior valid firmware when a corrupt package is offered.

An application update starts the verified installer with silent upgrade flags and then closes the running station. Since this is a machine-wide install, Windows may request administrator approval. If the installer cannot start or complete, the existing installation remains usable.

`installer/output` and `installer/work` are generated directories and are ignored by Git.

## Installed locations

Application files:

```text
C:\Program Files\Lord of Robots\LoR Core V3 Test Station
```

Writable production data:

```text
C:\ProgramData\Lord of Robots\LoR Core V3 Test Station
```

The ProgramData directory grants standard users write access. Results are deliberately preserved when the application is uninstalled or upgraded.

## Release validation

For every release:

1. activate the organization's Inno Setup commercial license on the release-builder account;
2. run the installer on a clean Windows test PC;
3. confirm the desktop and Start Menu shortcuts use the LoR icon;
4. launch the UI and confirm the animated logo, Live Test, Test History, and COM-port detection;
5. connect a known-good LoR Core and complete one full test using the bundled uploader;
6. confirm the CSV record appears under ProgramData;
7. calculate and publish the setup file's SHA-256 checksum;
8. retain the exact installer alongside the manufacturing release record.

The generated installer is not code-signed. Windows SmartScreen may therefore show an unknown-publisher warning on other PCs. A production release should be signed with the Lord of Robots Authenticode certificate before distribution. The evaluation installer built without an activated Inno Setup commercial license must not be treated as the final commercially distributed package.
