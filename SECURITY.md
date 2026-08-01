# Security Policy

## Supported versions

Security fixes are applied to the latest published Windows application and production-test firmware only.

| Component | Supported version |
|---|---:|
| Windows test station | Latest GitHub Release |
| Board test firmware | Firmware bundled with the latest Release |

## Reporting a vulnerability

Do not open a public issue for a suspected security vulnerability or include production board identifiers, Wi-Fi credentials, SSIDs, operator information, or manufacturing CSV data in an issue.

Use the repository's **Security → Report a vulnerability** workflow to submit a private GitHub Security Advisory:

https://github.com/LordofRobots/TestRig_LoR_Core_V3/security/advisories/new

Include the affected version, reproduction steps, expected impact, and the minimum diagnostic material needed to reproduce the issue. Lord of Robots will acknowledge the report, evaluate severity, and coordinate remediation before public disclosure.

## Update trust model

The station downloads only published, non-prerelease GitHub Release assets over HTTPS. It validates the release manifest, product identity, versions, package SHA-256 values, individual firmware-image SHA-256 values, and the exact approved ESP32 flash layout. Invalid or unavailable updates are rejected without replacing the active application or firmware.

The current installer is not Authenticode-signed, so Windows may show an unknown-publisher warning. Code signing remains recommended as a future defense-in-depth improvement.
