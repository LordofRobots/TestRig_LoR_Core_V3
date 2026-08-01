# Changelog

All notable production changes are recorded here. Application versions follow semantic versioning; board firmware uses the `production-test-x.y` scheme.

## Unreleased

### Added

- Native Android 0.1.0 engineering client for USB-host LoR Core testing
- CH340 detection, native ESP32 ROM flashing, guided checks, CSV history, and export
- Hash-verified synchronization from the common GitHub Release firmware package
- Android emulator build, install, launch, and responsive-layout validation

## [1.14.2] - 2026-08-01

### Added

- Public, tokenless update access through the project repository
- Professional architecture, security, licensing, issue-reporting, and release documentation
- Windows source-validation workflow for the main branch and pull requests
- Root `VERSION` file as the single application-version authority

### Changed

- Refined the public README with direct installation, status, operator, and support guidance
- Removed obsolete development caches and machine-specific shortcut artifacts
- Corrected the update-status separator encoding

## [1.14.1] - 2026-08-01

### Added

- Background GitHub Release checks for verified application and firmware updates
- SHA-256 validation for installers, firmware packages, and individual ESP32 images
- Versioned firmware caching with safe fallback to the bundled or last verified package
- Self-contained Windows installation using free, commercially usable NSIS tooling
- Deterministic update-manager validation, release manifests, and repeatable packaging

### Changed

- Reduced steady-state private memory from approximately 67 MB to approximately 25 MB by reusing one GIF image buffer
- Deferred Test History loading and bounded its in-memory view to the newest 2,000 records
- Preserved complete CSV history independently of the in-memory display limit
- Preserved ProgramData manufacturing records during upgrades and uninstall operations

### Verified

- Legacy silent upgrade from application 1.14.0
- Fresh install, uninstall, shortcuts, registry registration, and application restart
- Corrupt firmware rejection and rollback to the previous verified package
- Public, tokenless GitHub Release discovery

## [production-test-1.14] - 2026-07-31

- Added calibrated 20-sample VIN measurement with raw ADC reporting
- Added active BLE scanning and RSSI reporting
- Added confirmed ESP32 eFuse MAC identity formatting
- Added persistent red failure latch and two-second green pass indication
- Added spatial startup rainbow and icy-blue baseline animations
- Added continuous primary-color button feedback
- Limited measurements and RF scans to explicit station commands

[1.14.1]: https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/tag/v1.14.1
[1.14.2]: https://github.com/LordofRobots/TestRig_LoR_Core_V3/releases/tag/v1.14.2
[production-test-1.14]: production_test/lor_core_v3_production_test/lor_core_v3_production_test.ino
