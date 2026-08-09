# DESKTOP PACKAGING / STACK RESEARCH (Task 14)

Status: PHASE 0 RESEARCH — evaluation only, nothing is built.
Research date: 2026-08-09. All licence claims verified against primary sources; URLs inline.

## Comparison Table

| Option | Closed-source OK? | Licence | Payload (typical) | Windows quality | macOS path | AI-agent buildability | Key risk |
|---|---|---|---|---|---|---|---|
| Python + PyInstaller | **Yes** (explicit bootloader exception) | GPL-2.0+ with linking exception | adds ~10–20 MB over payload | Mature, first-class | Same tool works on macOS | Excellent | AV/SmartScreen false positives (mitigable) |
| PySide6 (Qt Widgets) | **Yes** under LGPL-3.0 with obligations | LGPL-3.0 / GPL-2.0 / GPL-3.0 (your choice) | wheel 77.5 MB (Essentials); trimmed app ~80–150 MB installed | Excellent, native-quality | Excellent (universal2 wheels) | Excellent | LGPL compliance discipline (notice, relink, source offer) |
| Tkinter | **Yes**, zero obligations of note | PSF + Tcl/Tk BSD-style | tiny (~10–15 MB packed) | Works, but dated look; HiDPI/theming weak | Works | Excellent | UI looks non-commercial without heavy theming |
| Flet | Yes (Apache-2.0) | Apache-2.0 | ~30–60 MB (bundles Flutter engine) | Good | Good | Good but API churn | Pre-1.0 (v0.86.5, Aug 2026) — breaking changes |
| Tauri v2 | Yes (MIT/Apache-2.0) | MIT OR Apache-2.0 | ~5–10 MB shell + Python sidecar (~30–60 MB) = no real saving | Good; needs WebView2 | Good (WKWebView) | Moderate — 3 toolchains | Complexity for zero benefit given Python core |
| .NET (C#/WPF) rewrite | Yes (.NET is MIT) | MIT | ~60–100 MB self-contained | First-class | WPF: **none** | Good, but reimplement parsers | Throws away the Python parsing ecosystem |

## Per-Option Findings

### 1. PyInstaller — licence VERIFIED, closed-source bundling explicitly permitted

- Licence: GPL "either version 2 of the License, or (at your option) any later version" **with a special Bootloader Exception**. Key sentence from `COPYING.txt`:
  > "In addition to the permissions in the GNU General Public License, the authors give you unlimited permission to link or embed compiled bootloader and related files into combinations with other programs, and to distribute those combinations without any restriction coming from the use of those files."
- The GPL still applies to PyInstaller itself; the bundled app is unrestricted. Source: https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt
- Bootloader question: covered by the same exception. No source disclosure of the app required.
- **AV false positives: real and recurring** (e.g. pyinstaller/pyinstaller#8164). Standard mitigations: use `--onedir` (not `--onefile`), code-sign every exe/DLL, optionally rebuild the bootloader from source, never use UPX, submit false positives to Microsoft. Sources: https://github.com/pyinstaller/pyinstaller/issues/8164, https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/

### 2a. PySide6 — VERIFIED

- Current version: **6.11.1** (May 13, 2026). Licence: `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Real payload: **PySide6-Essentials 77.5 MB (win x86-64 wheel)** + shiboken6; Addons optional and not needed for a Widgets app. Trimmed PyInstaller build typically 80–150 MB installed. Sources: https://pypi.org/project/PySide6/#files, https://pypi.org/project/PySide6-Essentials/#files
- **LGPL for a closed-source Python app — confirmed viable, no Qt commercial licence required if obligations are met** (Qt's own page: https://www.qt.io/licensing/open-source-lgpl-obligations):
  - Dynamic linking: PySide6 always uses Qt as shared DLLs — satisfied by construction.
  - Relink/replace: with a PyInstaller `--onedir` build the Qt DLLs sit as replaceable files on disk.
  - Notices: LGPL licence text must ship with the app and use of the LGPL library must not be hidden.
  - Source offer applies to **Qt itself** (not the app): link to the exact Qt source version suffices in practice.

### 2b. Tkinter

PSF License (https://docs.python.org/3/license.html) + Tcl/Tk BSD-style (https://www.tcl.tk/software/tcltk/license.html). Zero friction for closed-source. Lightest packaging (~10–15 MB) but does not read as a commercial product out of the box (dated widgets, weak HiDPI, no dark mode without third-party themes). Fallback option only.

### 2c. Flet

Apache-2.0, Flutter-rendered UIs from Python. **Still pre-1.0 (v0.86.5, Aug 1, 2026)** with historical breaking API changes. Not recommended as the foundation of a commercial product maintained long-term. Sources: https://github.com/flet-dev/flet/releases

### 3. Tauri v2

MIT OR Apache-2.0. Great shell size, but the core would need Rust/JS or a **Python sidecar** ("bundled using pyinstaller" per Tauri's own docs — https://v2.tauri.app/develop/sidecar/), inheriting all PyInstaller issues *plus* a Rust toolchain, JS frontend and IPC boundary. WebView2 bootstrap on clean Win10 wants network access — a wrinkle for an offline-marketed product. Verdict: poor fit.

### 4. Installers & code signing

- **Inno Setup** — free for commercial use, verified: "Permission is granted to anyone to use this software for any purpose, including commercial applications, and to alter and redistribute it". Source: https://jrsoftware.org/files/is/license.txt
- **NSIS** — zlib/libpng licence, equally free; more scriptable, less batteries-included. Source: https://nsis.sourceforge.io/License
- **Code signing reality (2026):** EV's instant-SmartScreen-bypass was removed in 2024 — EV and OV now build reputation the same way. OV certs ~$250–550/yr (cloud/HSM-backed). **Microsoft Trusted Signing ("Azure Artifact Signing") is the cost leader: $9.99/mo Basic** — but identity validation has eligibility constraints (orgs generally need 3+ years verifiable history; individual signup availability varies by region). Unsigned PyInstaller output = near-guaranteed SmartScreen warnings; signing is effectively mandatory. Sources: https://azure.microsoft.com/en-gb/pricing/details/trusted-signing/, https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options

### 5. .NET (C#/WPF) rewrite — rejected

.NET is MIT and some parsing libraries exist (Livo.MT940Parser, SharpMT940Lib, Sepa.Net), but the ecosystem is thin and mostly low-maintenance hobby libraries versus Python's actively maintained `mt940` (BSD) + openpyxl chain. A rewrite buys nothing on licensing, costs the entire parsing layer, and WPF forecloses macOS.

---

## RECOMMENDATION (single direction)

**Python 3.12+ core → PySide6 (Qt Widgets, LGPL-3.0) UI → PyInstaller `--onedir` build → Inno Setup installer → signed via Microsoft Trusted Signing (fallback: OV cert).**

Justification:
1. Licensing fully clean for closed-source at every layer, verified against primary sources. Zero licence fees.
2. Keeps the Python parsing ecosystem — the only layer with real domain risk.
3. PySide6 is the only Python GUI that reads as a commercial product and has a stable, deeply documented API.
4. `--onedir` + code signing simultaneously solves the LGPL relink obligation, the AV false-positive problem, and SmartScreen.
5. macOS later: identical stack (PySide6 universal2 wheels; PyInstaller .app bundles); only the installer changes.
6. Expected footprint: ~90–140 MB installed, ~50–80 MB compressed installer.

## Licence-Compliance Checklist (for the chosen direction)

- [ ] Ship Qt/PySide6 **unmodified** as shared libraries; never attempt static bundling of Qt.
- [ ] Include full text of **LGPL-3.0 and GPL-3.0** in the install dir and About dialog.
- [ ] **Prominent notice**: "This application uses the Qt framework via PySide6 under the GNU LGPL v3".
- [ ] Provide a link to the exact Qt source version used (download.qt.io archive) in the About dialog.
- [ ] Confirm users can **replace the Qt DLLs** in the install folder (no runtime hash-locking of Qt DLLs).
- [ ] PyInstaller: no obligations for the bundled app; do not distribute a modified bootloader without its source.
- [ ] Audit every Python dependency licence at build time (`pip-licenses` in CI); allow MIT/BSD/Apache/PSF/LGPL-dynamic; **block GPL/AGPL** runtime deps.
- [ ] Keep Inno Setup's copyright notice intact in the installer.
- [ ] Generate a THIRD-PARTY-NOTICES file listing all bundled packages + licences, installed with the app.

## Owner Action Items (feeds SOURCE-PACK.md)

1. **Code signing (blocking, do first — reputation takes weeks):** Apply for Microsoft Trusted Signing ($9.99/mo Basic); check eligibility for your legal entity/country. If ineligible, buy an OV cloud-HSM cert (~$250–550/yr). Do **not** pay the EV premium.
2. Decide the **legal entity name** for the certificate and SmartScreen prompts before purchase.
3. Accept a SmartScreen reputation-building window after each new cert; plan a soft launch.
4. Confirm decision to use the **LGPL route, no Qt commercial licence**.
5. Set up VirusTotal scanning of every release and a false-positive submission process.
6. Optional hardening: rebuild the PyInstaller bootloader from source in CI.
