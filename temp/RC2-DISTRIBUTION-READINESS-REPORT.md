# RC2 DISTRIBUTION READINESS REPORT — Bank Statement Format Studio V1

> **⚠ RC2 SUPERSEDED BY RC3 (2026-08-14).** After this report, the owner's
> VirusTotal scan of RC2 returned 2/70 heuristic detections; the
> investigation and fix (installer PE version resource completed) are in
> `temp/RC3-AV-FALSE-POSITIVE-REPORT.md`. Everything in this report keyed
> to hash `7e1cd5c8…042a` now applies to the **RC3** installer hash
> `f393f34968cd4e703506d8ab2def2b341f7de59ca0485ebe4851eb6fe6a8f340`
> (customer package reassembled as `RC3-customer-package/` and
> re-audited). The CONDITIONAL GO verdict stands, against the RC3 hash.

Date: 2026-08-14
Scope: RC2 freeze verification, VirusTotal status, distribution-compliance
audit, customer distribution package, package integrity. Per the binding plan
(`temp/Bank Statement Format Studio — RC2 & Distribution Readiness Plan.md`):
no clean-VM certification performed or documented, no marketplace listing
created, no Gumroad product created, nothing published, no ITISYOU page work,
no product changes.

---

## 1. RC2 identity (FROZEN)

| Field | Value |
|---|---|
| Designation | **Bank Statement Format Studio V1 RC2** |
| Installer | `packaging/Output/BankFormatStudio-1.0.0-setup.exe` |
| Size | 36,889,429 bytes |
| SHA-256 | `7e1cd5c8898b9c9cb56c222ddf5074bb2800f077bcb521626551e9b110a5042a` |
| Inner exe SHA-256 | `75b1f58543e05e546d70c7dbd8122174cbb5ad973c52478e43fd7c54790ddd41` |
| Source commit | `48d3a53` (icon-fix rebuild, pushed to `main`) |
| Version | 1.0.0 (installer AppVersion, exe version resource, pyproject) |
| Publisher | Leela Aravind Karlapudi · Brand: ITISYOU |
| Support | support@itisyou.app |
| Signing | **UNSIGNED** per `docs/UNSIGNED-RELEASE-POLICY.md` (never present as signed) |
| Supersedes | RC1 installer `308ffce4…0799` (2026-08-10) — failed manual visual verification; **must never be published** |

The installer's SHA-256 was **independently recomputed** at RC2 freeze with
`Get-FileHash` and matches both the expected value and the build-generated
`SHA256SUMS.txt`. The artifact was **not rebuilt** and is preserved
byte-for-byte. Any binary change invalidates RC2 and requires a new hash.

## 2. Verification & CI evidence (non-artifact-changing)

- Working tree at freeze: clean on `main` at `48d3a53` (only the plan file
  untracked; committed with this report).
- Full pytest: **269 passed / 0 failed / 0 skipped** (unit, golden,
  security under the socket-blocking harness, GUI offscreen,
  release-packaging incl. the 7 icon-regression tests).
- ruff: all checks passed.
- Licence gate: passed — 16 shipped-candidate distributions, zero GPL/AGPL.
- PE re-inspection of the frozen artifacts: app exe 6/6 and installer exe
  6/6 RT_ICON resources byte-match `packaging/logo.ico`;
  `_internal/logo.ico` byte-identical (runtime Qt icon source).
- GitHub Actions CI on `48d3a53`: run **31813273818**, completed
  **success** (2026-08-14).
- Build provenance: `packaging/build.ps1` 8/8 exit 0 on 2026-08-14, pinned
  venv, Python 3.14.0, PyInstaller 6.22.0, Inno Setup 6 (recorded in
  `temp/RELEASE-CANDIDATE-REPORT.md`).

## 3. VirusTotal

**OWNER ACTION REQUIRED — VIRUSTOTAL**

No authorized VirusTotal access exists in this environment (no API key, no
`vt` CLI, no configuration). An anonymous web upload would place the
artifact in VirusTotal's public corpus without the owner's explicit
authorization, so no submission was made. **No VirusTotal PASS is claimed.**

The owner must submit **exactly this file**:

- File: `packaging/Output/BankFormatStudio-1.0.0-setup.exe`
- SHA-256 (verify before upload):
  `7e1cd5c8898b9c9cb56c222ddf5074bb2800f077bcb521626551e9b110a5042a`

Evidence to return/record:

1. The SHA-256 VirusTotal displays for the submission (must equal the above).
2. Scan date, detection count (x/y engines) and each detecting vendor +
   detection name.
3. The VirusTotal report URL.
4. Investigation of any detections — PyInstaller-packaged apps have a known
   elevated heuristic false-positive rate, but **detections must be
   investigated, not assumed benign**. Credible malware findings block the
   release; probable heuristics get submitted to Microsoft/vendors as
   false-positive reports (policy §3.3).

Never upload source code, bank data, fixtures, credentials or secrets —
only the installer above.

## 4. Distribution / marketplace compliance audit

Positioning verified against actual V1 functionality: **an offline Windows
utility that converts and validates bank-statement formats (MT940,
ISO 20022 camt.053.001.02/.08, its documented CSV dialect, XLSX
export-only)**, with balance reconciliation and per-conversion
information-loss reporting. It is not an AI product, not banking software,
and not banking/accounting/tax/legal/financial advice — the EULA,
About dialog and customer docs all state this; no material claims otherwise;
no "lossless" claim exists anywhere (SEC-23 enforced by tests).

### PASS

- **Product identity**: consistent name/version 1.0.0 across installer,
  exe version resource, EULA, About, customer docs (test-enforced).
- **Publisher identity**: Leela Aravind Karlapudi in installer
  `AppPublisher`, exe `CompanyName`, EULA, customer docs (test-enforced).
- **EULA**: complete, final release values (date 10 August 2026, support
  contact), `docs/EULA.md` ↔ `packaging/EULA.txt` synchronized
  (test-enforced), shown and required by the installer, shipped in the
  install dir, statutory consumer rights expressly preserved, third-party
  licences expressly not overridden.
- **Third-party licensing / LGPL obligations**: PySide6/shiboken6 under
  LGPL-3.0 with the relink obligation satisfied (onedir build, Qt DLLs
  replaceable on disk — build-enforced); `THIRD-PARTY-NOTICES.txt` +
  LGPL-3.0/GPL-3.0 texts shipped in the installer and the customer
  package; About dialog carries the LGPL notice and Qt source instructions;
  licence gate proves zero GPL/AGPL runtime dependencies.
- **Privacy/offline claims**: accurate — no network code paths (security
  suite runs under a socket-blocking harness), no telemetry, data in
  memory only until the user saves; claims match `docs/SECURITY-REQUIREMENTS.md`.
- **Supported formats & limitations**: accurately documented for customers
  (`SUPPORTED-FORMATS.md`, `CSV-DIALECT.md`), including XLSX export-only,
  CSV dialect-only import, unsupported formats, Windows-only.
- **System requirements**: documented for customers (Windows 10 64-bit
  1809+/11, ~150 MB, per-user install, no admin, no internet).
- **Unsigned status & SmartScreen disclosure**: honest customer guidance in
  `INSTALL-AND-VERIFY.md` per policy §5 — expected warnings explained,
  SHA-256 verification steps first, protections never weakened or disabled.
- **Checksum instructions**: exact `Get-FileHash` command + expected hash in
  the guide and `SHA256SUMS.txt` in the package.
- **Support contact**: support@itisyou.app in EULA and customer docs.
- **Prohibited-category check (Gumroad)**: self-authored proprietary
  utility software; not a money-service/financial-advice/crypto/hacking
  product; nothing in Gumroad's prohibited list applies
  (gumroad.com/prohibited, checked 2026-08-14).

### OWNER ACTION

1. **VirusTotal** — §3 above (policy §3.3 makes this mandatory before
   publication).
2. **Manual visual icon/branding verification** of RC2 (outstanding from
   the icon-fix rebuild; checklist item in `docs/RELEASE-CHECKLIST.md`).
   Automated resource verification is done; human eyes are not.
3. **Clean-VM certification** (install on networking-disabled Windows
   10/11 VM, functional pass) — required by the release checklist; out of
   scope for this session by instruction.
4. **Publish `SHA256SUMS.txt` in two independent channels** at release
   time (policy §3.2).
5. **Download/product page carries the §5 disclosure text** and release
   notes state "unsigned" (policy §3.4) — wording ready in
   `docs/UNSIGNED-RELEASE-POLICY.md`.
6. **Define the customer refund position** for the listing (see
   marketplace requirements below); the EULA intentionally leaves statutory
   rights intact and states no refund policy of its own.

### MARKETPLACE-SPECIFIC REQUIREMENT (Gumroad, verified 2026-08-14)

- Seller must **set a refund policy** per product (none/7/14/30/183 days +
  optional fine print); Gumroad additionally reserves the right to refund
  within 90 days at its discretion to prevent chargebacks.
- **Account standing**: new accounts face verification and possible payout
  holds; payout details must be configured.
- **Accurate listing**: description must match actual functionality (the
  PASS positioning above is the approved wording basis).
- Gumroad acts as reseller/merchant-of-record for tax collection in most
  regions — confirm current terms during listing setup.
- Sources: [gumroad.com/prohibited](https://gumroad.com/prohibited),
  [Gumroad refund policy help](https://gumroad.com/help/article/51-what-is-gumroads-refund-policy),
  [refund policy blog](https://gumroad.com/blog/p/specify-a-refund-policy-for-your-products),
  [Gumroad ToS](https://gumroad.com/terms).

### BLOCKER

- **None identified in the product or package.** The gating items above are
  process gates (owner actions), not product defects.

## 5. Customer distribution package

Location: `packaging/Output/RC2-customer-package/` (inside gitignored
`packaging/Output/` — release binaries stay out of the repository per
policy; the two authored guides are tracked at `packaging/customer/`).

| File | Size (bytes) | Role |
|---|---|---|
| `BankFormatStudio-1.0.0-setup.exe` | 36,889,429 | exact RC2 installer |
| `SHA256SUMS.txt` | 187 | checksum manifest (installer + inner exe) |
| `EULA.txt` | 4,632 | licence agreement (identical to installed copy) |
| `INSTALL-AND-VERIFY.md` | 3,728 | install guide, sysreqs, unsigned/SmartScreen guidance, hash verification |
| `SUPPORTED-FORMATS.md` | 2,320 | supported formats + V1 limitations |
| `CSV-DIALECT.md` | 3,676 | customer CSV interchange documentation |
| `THIRD-PARTY-NOTICES.txt` | 4,145 | third-party attribution (build-generated) |
| `licenses/LICENSE.LGPL3.txt` | 7,652 | LGPL-3.0 text |
| `licenses/LICENSE.GPL3.txt` | 35,149 | GPL-3.0 text (LGPL Section 4 companion) |

Excluded and verified absent: source code, tests, fixtures, repository
metadata, build scripts, internal audits/specs, temp files, credentials,
secrets, superseded RC1 installer. The guidance never instructs disabling
Defender/SmartScreen; it describes only the standard per-file Windows flow
after hash verification.

## 6. Package integrity results

- Installer in the package **byte-identical** to frozen RC2
  (`7e1cd5c8…042a` recomputed on the packaged copy). ✅
- `SHA256SUMS.txt` installer line matches the recomputed hash. ✅
- Superseded RC1 hash `308ffce4…0799` appears **nowhere** in the package
  (full recursive scan). ✅
- Placeholder/secret scan (`[INSERT`, `[RELEASE DATE]`, TODO/FIXME/
  CHANGEME, `OWNER-LEGAL`, example.com, key/password patterns): **zero
  hits**. ✅
- Identity: product name, version 1.0.0, publisher and support contact
  present and consistent across all customer documents. ✅
- Required legal docs present: EULA, third-party notices, LGPL-3.0 +
  GPL-3.0 texts. ✅
- No internal/development material in the inventory (10 files total,
  listed above). ✅

## 7. Outstanding owner actions before Gumroad launch

In order:

1. Manual visual icon/branding verification of RC2 (checklist item).
2. VirusTotal submission of the exact RC2 installer + evidence (§3).
3. Clean-VM certification per `docs/RELEASE-CHECKLIST.md` (networking
   disabled, functional conversion pass, SEC-01/SEC-06 checks).
4. Gumroad account setup: identity/payout verification; set refund policy.
5. Listing content: accurate positioning (per §4 PASS wording), §5 unsigned
   disclosure text, `SHA256SUMS.txt` contents on the page **and** in a
   second independent channel; release notes state "unsigned".

## 8. Verdict

**CONDITIONAL GO** for proceeding to Gumroad setup.

The product, artifact, documentation and customer package are ready and
audited with no blockers. The conditions are the five owner actions in §7 —
notably manual visual verification, VirusTotal evidence and clean-VM
certification, which must all pass against **this exact hash**
(`7e1cd5c8…042a`) before anything is published. If any of them fails or the
binary changes for any reason, RC2 is invalidated: a new hash must be
generated and every downstream check repeated.
