# RC3 — VirusTotal Detection Investigation & Remediation Report

Date: 2026-08-14
Trigger: owner's VirusTotal scan of RC2 installer
(`7e1cd5c8898b9c9cb56c222ddf5074bb2800f077bcb521626551e9b110a5042a`)
returned **2/70 detections**: Microsoft `Trojan:Win32/Wacatac.B!ml` and
Arctic Wolf `Unsafe`.

## 1. Investigation (before any change)

### Local reproduction attempt

Microsoft Defender on the build machine — engine 4.18.26070.9, signatures
1.457.156.0, updated 2026-08-14 (same day) — was run against both the exact
RC2 installer and the entire frozen onedir tree with remediation disabled:

- `BankFormatStudio-1.0.0-setup.exe`: **no threats found**
- `packaging/dist/BankFormatStudio/` (full tree, all DLLs/pyds): **no
  threats found**

A current, full local Defender engine does **not** flag the artifact. The
VT "Microsoft" verdict therefore does not come from a signature match but
from the ML-only classification path (`!ml` suffix = machine-learning
verdict). `Wacatac.B!ml` is the most widely reported false-positive label
for unsigned PyInstaller-frozen applications and Inno Setup installers with
zero prevalence.

Arctic Wolf's VT engine is a reputation/ML classifier; `Unsafe` is its
generic verdict for low-prevalence unsigned executables and commonly
co-fires alongside any other engine's heuristic hit. It names no family and
no behaviour.

### Build/dependency audit for false-positive triggers

| Surface | Finding |
|---|---|
| PyInstaller (6.22.0, PyPI wheel) | onedir (not onefile), no UPX, standard bootloader, `console=False`, default asInvoker manifest — all already the low-FP configuration; nothing to change |
| Bundled dependencies | all hash-pinned wheels from PyPI (`requirements.lock`, `--require-hashes` proof in CI); licence gate enumerates 16 distributions; local Defender scan of every bundled binary: clean |
| App exe metadata | complete version resource (CompanyName/FileDescription/FileVersion 1.0.0.0/ProductName/Copyright/OriginalFilename) — no gap |
| **Installer exe metadata** | **DEFECT: binary FILEVERSION was 0.0.0.0, `FileVersion` string empty, `InternalName`/`OriginalFilename` empty** — Inno Setup leaves these unset unless `VersionInfo*` directives are given. Missing/zeroed version metadata on an unsigned executable is a classic ML-heuristic false-positive contributor and poor transparency in the file Properties dialog |
| Installer behaviour | per-user, no elevation, fully offline, LZMA2 — nothing heuristically aggressive |
| Signing | unsigned (£0 path, `docs/UNSIGNED-RELEASE-POLICY.md`) — the single largest reputation factor; unchangeable without a certificate (owner exit criteria already documented) |

### Root-cause conclusion

The detections are **reputation/ML heuristics on an unsigned, zero-
prevalence PyInstaller+Inno artifact**, aggravated by the installer's
incomplete PE version resource. No evidence of any real malicious
indicator: current-signature Defender passes the artifact and every
bundled component; all inputs are hash-pinned public wheels; the build is
reproducible from the repository.

## 2. Remediation (RC3)

Principle honoured: **no application functionality was weakened, removed or
altered**, and no obfuscation/packing/bootloader-rebuild tricks were used.
The only change is completing legitimate, user-visible metadata:

`packaging/installer.iss` — added to `[Setup]`:

```
AppContact=support@itisyou.app
VersionInfoVersion=1.0.0.0
VersionInfoDescription=Bank Statement Format Studio Setup
VersionInfoCompany=Leela Aravind Karlapudi
VersionInfoCopyright=Copyright (C) 2026 Leela Aravind Karlapudi
VersionInfoOriginalFileName=BankFormatStudio-1.0.0-setup.exe
```

New regression test `test_installer_exe_version_resource_is_complete`
(tests/unit/test_release_packaging.py) pins all six directives. Suite grows
269 → **270 tests**.

`packaging/customer/INSTALL-AND-VERIFY.md` updated to the RC3 hash; the
customer package was reassembled as `packaging/Output/RC3-customer-package/`
and re-audited (installer byte-identical to RC3, sums match, no superseded
hashes anywhere, inventory unchanged otherwise).

## 3. RC3 identity and verification

| Field | Value |
|---|---|
| Designation | **Bank Statement Format Studio V1 RC3** |
| Installer | `packaging/Output/BankFormatStudio-1.0.0-setup.exe` |
| Size | 36,892,164 bytes |
| **SHA-256** | `f393f34968cd4e703506d8ab2def2b341f7de59ca0485ebe4851eb6fe6a8f340` |
| Inner exe SHA-256 | `75b1f58543e05e546d70c7dbd8122174cbb5ad973c52478e43fd7c54790ddd41` — **byte-identical to RC2's** (deterministic PyInstaller output; proves only the installer layer changed) |
| Version | 1.0.0 (unchanged) |
| Supersedes | RC2 `7e1cd5c8…042a` (metadata-incomplete installer; never published) and RC1 `308ffce4…0799` |

Verification of RC3:

- Build pipeline `packaging/build.ps1`: 8/8, exit 0 (licence gate → full
  pytest **270 passed** → notices → licence texts → PyInstaller → frozen
  smoke incl. Qt-DLL check → Inno Setup → SHA-256 manifest)
- ruff: clean; licence gate: 16 distributions, zero GPL/AGPL
- Installer version resource now complete: binary FileVersion 1.0.0.0,
  OriginalFilename `BankFormatStudio-1.0.0-setup.exe`, company/description/
  copyright populated (verified on the built artifact)
- PE icon inspection: app exe 6/6 and installer 6/6 RT_ICON byte-match
  `logo.ico`; `_internal/logo.ico` byte-identical
- Local Defender (current signatures): RC3 installer **no threats found**

## 4. Honest expectations and remaining owner actions

Completing the version resource removes a known heuristic trigger, but the
dominant factors — **unsigned binary + zero prevalence** — remain until the
release is signed and/or gains reputation. A residual ML flag on a fresh
VirusTotal scan is possible; that is what vendor false-positive submission
is for. Do not present any scan outcome as "signed/verified".

1. **Submit RC3 to VirusTotal** (exact file above; verify the SHA-256
   before upload). Record the report URL, date, detection count and vendor
   names.
2. If Microsoft still flags it: submit the installer to Microsoft Security
   Intelligence (https://www.microsoft.com/en-us/wdsi/filesubmission) as a
   **software developer / false positive** report, referencing
   `Trojan:Win32/Wacatac.B!ml`, and record the submission ID. Microsoft
   typically clears confirmed FPs within days; cloud verdicts update
   without a new build.
3. If Arctic Wolf still flags it: report the false positive to Arctic Wolf
   (falsepositive@arcticwolf.com per their VT engine listing) with the
   hash and VT link.
4. All downstream gates (manual visual verification, clean-VM
   certification, two-channel `SHA256SUMS.txt` publication, disclosure
   text) now apply to the **RC3 hash** `f393f349…a8f340`. RC1/RC2 hashes
   must never be published.
5. Signing remains the structural fix (policy §6 exit criteria) whenever
   the owner obtains Authenticode access.

**Not done, by instruction:** no Gumroad publication, no marketplace
listing, no clean-VM certification claim, no VirusTotal upload from this
environment (owner-authorized submission only).
