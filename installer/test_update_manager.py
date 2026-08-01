"""Deterministic validation for the GitHub app/firmware update pipeline."""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "production_test"))

import lor_core_test_station as station  # noqa: E402


def run() -> None:
    bundled = (
        PROJECT_ROOT
        / "installer"
        / "output"
        / "app"
        / "LoR Core V3 Test Station"
        / "_internal"
        / "firmware"
    )
    if not bundled.exists():
        raise FileNotFoundError("Build the installer before running this test")

    test_temp_root = PROJECT_ROOT / "tmp"
    test_temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lor-update-test-", dir=test_temp_root) as temporary:
        temporary_dir = Path(temporary)
        station.PACKAGED_FIRMWARE = bundled
        station.FIRMWARE_CACHE_ROOT = temporary_dir / "firmware-cache"
        station.DATA_ROOT = temporary_dir / "data"
        manager = station.UpdateManager()

        with (bundled / station.FIRMWARE_MANIFEST_NAME).open("r", encoding="utf-8") as stream:
            future_firmware = json.load(stream)
        future_firmware["version"] = "production-test-9.99"

        firmware_zip = temporary_dir / "future-firmware.zip"
        with zipfile.ZipFile(firmware_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in future_firmware["files"]:
                archive.write(bundled / item["name"], item["name"])
        future_firmware["package_asset"] = firmware_zip.name
        future_firmware["package_sha256"] = station.file_sha256(firmware_zip)

        installer = temporary_dir / "future-setup.exe"
        installer.write_bytes(b"verified deterministic installer fixture")
        app = {
            "version": "9.99.0",
            "asset": installer.name,
            "sha256": station.file_sha256(installer),
        }
        release_manifest = {
            "schema": 1,
            "product": "LoR Core V3 Test Station",
            "app": app,
            "firmware": future_firmware,
        }
        assets = {
            firmware_zip.name: {"browser_download_url": "fixture://firmware"},
            installer.name: {"browser_download_url": "fixture://installer"},
        }
        downloads = {
            "fixture://firmware": firmware_zip,
            "fixture://installer": installer,
        }
        manager._find_update_release = lambda: (release_manifest, assets)  # type: ignore[method-assign]
        manager._download = lambda url, destination, maximum=station.MAX_DOWNLOAD_BYTES: shutil.copy2(  # type: ignore[method-assign]
            downloads[url], destination
        )

        result = manager.check_for_updates()
        package_dir, manifest, source = manager.firmware_package()
        assert result["firmware_updated"] is True
        assert manifest["version"] == "production-test-9.99"
        assert source == "downloaded"
        assert package_dir.is_dir()
        assert Path(result["installer"]).is_file()

        corrupt = copy.deepcopy(release_manifest)
        corrupt["firmware"]["version"] = "production-test-10.0"
        corrupt["firmware"]["package_sha256"] = "0" * 64
        manager._find_update_release = lambda: (corrupt, assets)  # type: ignore[method-assign]
        try:
            manager.check_for_updates()
        except ValueError:
            pass
        else:
            raise AssertionError("A corrupt firmware package was accepted")
        assert manager.firmware_package()[1]["version"] == "production-test-9.99"

    print("Update manager validation passed")


if __name__ == "__main__":
    run()
