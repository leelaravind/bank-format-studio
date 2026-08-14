# ANTIVIRUS RELEASE DECISION — Bank Statement Format Studio V1

Date: 2026-08-14
Inputs: owner's VirusTotal report for RC2 (saved page preserved at
`temp/VirusTotal - File - 7e1cd5c8…042a.html`, confirming 2/70), local
Defender scans, PE/metadata audit, source audit, sandbox-behaviour analysis
extracted from the saved VT report (CAPE Sandbox + Zenbox tabs).

Constraint honoured throughout: nothing was changed to *evade* detection;
no functionality was weakened; the only binary change (RC3) fixes a real
metadata defect that should have been correct regardless of any scanner.

---

## 1. Root-cause matrix

| Signal | Observed evidence | Origin | Malicious? |
|---|---|---|---|
| Microsoft `Trojan:Win32/Wacatac.B!ml` | `!ml` suffix = machine-learning-only verdict. Local Defender (engine 4.18.26070.9, sigs 1.457.156.0, same-day 2026-08-14) scans the identical file and full dist tree **clean** — no signature match exists. Label is the most common FP family for unsigned PyInstaller/Inno artifacts | **PYINSTALLER + INNO SETUP packaging shape + unsigned/zero-prevalence reputation** (not app code) | No evidence. ML heuristic |
| Arctic Wolf `Unsafe` | Generic reputation verdict; names no family, no behaviour; co-fires on low-prevalence unsigned files | **Unsigned + zero prevalence** (reputation classifier) | No evidence |
| "Process Injection" (MITRE T1055 chip) | The report contains **zero** occurrences of any injection API — WriteProcessMemory 0, CreateRemoteThread 0, NtMapViewOfSection 0, QueueUserAPC 0, SetThreadContext 0. The chip is a sandbox technique-mapping of the Inno two-stage bootstrap (`setup.exe` extracts and runs `%TEMP%\is-1YUEQ9A6JQ.tmp\BankFormatStudio-1.0.0-setup.tmp`) | **INNO SETUP** (standard bootstrap), sandbox heuristic mapping | No. No injection API evidence at all |
| Registry activity | Extracted keys: `HKCU\Software\Borland\Delphi\Locales` + `Borland\Locales` (Inno is Delphi-built; classic locale probe), `HKCU\...\RestartManager\Session0000\*` (Windows Restart Manager, used by Inno CloseApplications), `HKCU\...\Uninstall\{6E7B62F1-9C64-4A7E-A87A-BFS…}` (**our own per-user uninstall key — the intended installation record**), Explorer/Themes/Search shell keys | **INNO SETUP + WINDOWS INSTALLATION** (uninstall key: intended product behaviour) | No. All expected; per-user scope only (SEC-22, no HKLM writes) |
| Installer temp-process behaviour | `is-XXXX.tmp` staging files and the `setup.tmp` child process; "self-delete" chip = Inno removing its extracted temp copy after install | **INNO SETUP** by design | No |
| "persistence" chip | Maps to the uninstall registry key + Start Menu shortcut — i.e. *being installed*. No Run keys, no services, no scheduled tasks, no startup entries appear anywhere in the report | **WINDOWS INSTALLATION** (intended) | No |
| Network comms | The **entire** recorded network activity is one `UDP 162.159.36.2:53` packet — a DNS query to Cloudflare's public resolver, i.e. sandbox-VM background noise. **No TCP connections, no HTTP, no contacted domains/URLs.** Memory-pattern domain found: `jrsoftware.org` — Inno Setup's own homepage string embedded in every Inno installer | **Sandbox environment + INNO SETUP string constant** | No. Corroborates the offline claim |
| Dropped files (56) | The install payload itself: `BankFormatStudio.exe`, `_internal\PySide6\Qt6*.dll`, `MSVCP140*.dll`, staged `is-*.tmp` copies | **INNO SETUP + QT/DEPENDENCIES** (intended) | No |

Nothing lands in UNKNOWN and **nothing attributes to APPLICATION CODE** —
consistent with the app being a thin Qt GUI over a pure conversion library.

## 2. Security evidence against each threat hypothesis

| Hypothesis | Finding | Evidence |
|---|---|---|
| Malicious code | **No evidence** | Same-day-signature Defender: RC2 installer, RC3 installer and full dist tree all clean; no CAPE "Malware Config" extracted (0 hits); no detection is signature-based |
| Unexpected network activity | **None** | Sandbox: zero TCP/HTTP, zero contacted domains; source tree has **zero** network references (`socket`/`urllib`/`requests`/`http.client`/`QtNetwork`/`urlopen`/`WinHttp` — no matches in `src/`); QtNetwork Python module excluded in the spec; the security suite runs under a socket-blocking harness. `Qt6Network.dll` ships as a PySide6 binary-dependency artifact but is never imported by the app — kept, because removing shipped Qt DLLs to influence scanners would be evasion-motivated tampering |
| Persistence outside intended installation | **None** | Only the per-user uninstall key + shortcuts; no Run keys/services/tasks in the entire behaviour report |
| Credential/data collection | **None** | No such APIs/paths in source; statement data is memory-only until user-save (SEC posture, test-enforced); no telemetry |
| Unauthorized process manipulation | **None** | Zero injection-API occurrences; only Inno's own child bootstrap process |
| Suspicious bundled dependency | **None** | All dependencies are hash-pinned PyPI wheels (`requirements.lock`; CI `--require-hashes` install proof); licence gate enumerates all 16 shipped distributions; every bundled binary Defender-scanned clean |
| Build-machine contamination | **No indication** | Build inputs are hash-verified wheels + this repository; outputs scan clean with current signatures; inner exe reproduces **byte-identically** across the RC2→RC3 rebuilds (`75b1f585…`), which contamination of the build path would have broken |

## 3. RC2 vs RC3 decision

Criterion 3 (clean → don't rebuild) vs criterion 4 (real defect → fix → RC3):
**criterion 4 applied.** The audit found a genuine packaging defect
independent of any scanner: the Inno setup exe shipped with an incomplete
PE version resource (binary FILEVERSION `0.0.0.0`, empty
FileVersion/OriginalFilename/InternalName). That is a transparency defect
customers can see in the file's Properties dialog, and fixing it required a
rebuild. It happens to also remove a documented ML-heuristic contributor —
but it is not an evasion change and would be correct even if VT did not exist.

**Why the binary changed, exactly:** six `[Setup]` metadata directives in
`packaging/installer.iss` (`VersionInfoVersion/Description/Company/
Copyright/OriginalFileName`, `AppContact`). Nothing else. Proof of scope:
the inner `BankFormatStudio.exe` is **byte-identical** between RC2 and RC3
(`75b1f58543e05e546d70c7dbd8122174cbb5ad973c52478e43fd7c54790ddd41`);
only the Inno wrapper differs.

| | RC2 (invalidated) | **RC3 (current)** |
|---|---|---|
| Installer | `BankFormatStudio-1.0.0-setup.exe` | `BankFormatStudio-1.0.0-setup.exe` |
| SHA-256 | `7e1cd5c8898b9c9cb56c222ddf5074bb2800f077bcb521626551e9b110a5042a` | **`f393f34968cd4e703506d8ab2def2b341f7de59ca0485ebe4851eb6fe6a8f340`** |
| Size | 36,889,429 | 36,892,164 |
| Status | superseded, never publish | frozen, awaiting VT scan |

RC3 went through the approved pipeline (`packaging/build.ps1`, 8/8, exit 0)
with the complete suite inside it: **270 tests passed** (unit, golden,
security socket-blocking, GUI, release-packaging incl. the new
version-resource regression test), ruff clean, licence gate clean,
`SHA256SUMS.txt` regenerated, icon resources re-verified 6/6, RC3 installer
Defender-scanned clean. Customer package rebuilt as
`packaging/Output/RC3-customer-package/` and integrity-audited.

## 4. Vendor false-positive actions (owner)

The FP case is **evidence-supported, not assumed**: current-signature
Defender passes the file; the ML verdict has no signature, no behavioural
IOC, no network, no injection APIs, no persistence beyond installation.

**A new VirusTotal scan of RC3 is REQUIRED** (its hash has never been
scanned; RC2's VT results do not transfer to a different file).

1. Verify then submit RC3 to VirusTotal:
   `Get-FileHash packaging\Output\BankFormatStudio-1.0.0-setup.exe` must
   print `f393f349…a8f340`. Record report URL, date, x/70, vendor names.
2. **If Microsoft flags RC3**: submit the installer at
   https://www.microsoft.com/en-us/wdsi/filesubmission as *Software
   developer* → *Incorrectly detected* referencing
   `Trojan:Win32/Wacatac.B!ml`. Attach/state: unsigned Inno Setup installer
   of a PyInstaller-packaged offline desktop app; publisher Leela Aravind
   Karlapudi; no network code (offline converter); hash above. Keep the
   submission ID. Cloud ML verdicts clear without a rebuild.
3. **If Arctic Wolf flags RC3**: email falsepositive@arcticwolf.com with
   the hash, the VT link and the product description; record the reply.
4. Re-run VT re-analysis after vendor confirmation and record the final
   detection ratio alongside `SHA256SUMS.txt` publication.

## 5. Final verdict

**NEW RC REQUIRES VIRUSTOTAL.**

No credible evidence of malicious code, unexpected network activity,
persistence, data collection, process manipulation, dependency compromise
or build contamination exists — every sandbox signal is attributed to Inno
Setup mechanics, Windows installation, or unsigned/zero-prevalence
reputation. The release is safe to continue **on the RC3 artifact**
(`f393f349…a8f340`), which must receive its own VirusTotal scan (and, if
flagged, the vendor FP submissions above) before publication. RC1/RC2
hashes must never be published. Not published to Gumroad.
