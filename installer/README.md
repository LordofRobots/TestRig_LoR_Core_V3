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
- NSIS 3.x. NSIS is open source and permits commercial use without a paid license.

Install the Python packaging tools with:

```powershell
py -3 -m pip install --user pyinstaller esptool pyserial
```

Install NSIS with:

```powershell
winget install --id NSIS.NSIS --exact
```

## Build

From the repository root, run:

```powershell
.\installer\build-installer.ps1
```

Set the release version once in the repository-root `VERSION` file. The builder validates and applies it to the frozen UI, NSIS metadata, installer filename, and update manifest.

The script performs a clean release build:

1. compiles the production firmware with the `huge_app` partition scheme;
2. creates a versioned firmware ZIP and SHA-256 manifest;
3. builds a standalone esptool uploader;
4. freezes the UI and embeds the branding, updater, and verified fallback firmware;
5. compiles the free NSIS package;
6. creates the update manifest and collects the three GitHub Release assets.

The output is:

```text
installer\output\LoR_Core_V3_Test_Station_Setup_x.y.z.exe
```

Ready-to-publish assets are collected in:

```text
installer\output\release
```

## Publish an update

Create a normal, published GitHub Release in `LordofRobots/TestRig_LoR_Core_V3` and attach all three files from `installer\output\release`:

```text
LoR_Core_V3_Test_Station_Setup_x.y.z.exe
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

1. run the installer on a clean Windows test PC;
2. confirm the desktop and Start Menu shortcuts use the LoR icon;
3. launch the UI and confirm the animated logo, Live Test, Test History, and COM-port detection;
4. connect a known-good LoR Core and complete one full test using the bundled uploader;
5. confirm the CSV record appears under ProgramData;
6. calculate and publish the setup file's SHA-256 checksum;
7. retain the exact installer alongside the manufacturing release record.

The generated installer is not code-signed. Windows SmartScreen may therefore show an unknown-publisher warning on other PCs. Signing with a Lord of Robots Authenticode certificate is recommended when one becomes available, but it is not a licensing requirement. NSIS itself is free for personal and commercial use.
