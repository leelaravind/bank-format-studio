# RELEASE CHECKLIST (P1-M10 gate)

Run for every release build. Items marked OWNER require assets/credentials only
the owner holds; engineering must never fake them.

## Automated (enforced by `packaging/build.ps1` + CI)

- [ ] `python tools/licence_gate.py` passes (zero GPL/AGPL, LGPL only via documented exceptions)
- [ ] `pytest tests -q` fully green (unit + golden + security + GUI)
- [ ] Security suite ran under the socket-blocking harness (part of the full run)
- [ ] Generated camt outputs XSD-validate (writer self-validation is mandatory in code)
- [ ] Generated MT940 reparses + INV-7 conservation (enforced in-engine on every conversion)
- [ ] Deterministic outputs (golden byte-comparisons)
- [ ] THIRD-PARTY-NOTICES.txt regenerated and shipped
- [ ] LGPL-3.0 + GPL-3.0 texts shipped in `licenses/` (build fails without them)
- [ ] PyInstaller `--onedir` build; Qt DLLs present as replaceable files (checked by build script)
- [ ] No UPX (locked decision)
- [ ] Installer built with Inno Setup, per-user, no elevation (SEC-22), fully offline
- [ ] Frozen-app smoke test on the build machine

## Manual (per release)

- [ ] Install on a clean Windows 10/11 VM **with networking disabled**; open the app;
      convert one MT940 → camt.053.001.02 and one camt → CSV; verify reconciliation
      and loss reports render; save outputs (SEC-01 offline proof)
- [ ] Verify About dialog shows the LGPL notice and version
- [ ] Verify no files created outside the chosen output directory (SEC-06)
- [ ] Documentation/marketing wording contains no "lossless" claim and honest
      memory/disk wording (SEC-23)

## OWNER actions

- [ ] Code-sign `BankFormatStudio.exe` and the installer (Microsoft Trusted Signing
      or OV certificate). Configure the SignTool hook in `packaging/installer.iss`
      and the signing step in `packaging/build.ps1`. **Never released unsigned.**
- [ ] Set `AppPublisher` in `packaging/installer.iss` to the legal entity name
- [ ] Provide a product icon (`packaging/` → `bfs.spec` icon field)
- [ ] Upload release to VirusTotal; submit any false positives to Microsoft
- [ ] SmartScreen reputation plan (soft launch) per docs/PACKAGING-STACK-RESEARCH.md
- [ ] Lemon Squeezy / Gumroad listing (future phase)
