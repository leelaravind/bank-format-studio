# FINAL RELEASE AUDIT — Bank Statement Format Studio V1

Audit date: 2026-08-09. Independent, adversarial, read-only audit per
`temp/RELEASE-AUDIT-GOAL.md`. Method: four independent domain audits (financial
correctness & round-trip/loss; security & privacy; packaging/licensing/CI/identity;
scope & test quality) plus orchestrator-level cross-environment spot checks.
Nothing in the repository was modified; no golden files were regenerated; no
tests were altered. Evidence classes are labelled: [verified fact] = executed
verification, [static] = code inspection, [manual] = owner-only requirement,
[inference] = engineering judgement.

---

## A. VERIFIED CLAIMS

| Claim (IMPLEMENTATION-COMPLETION-REPORT.md) | Status | Evidence |
|---|---|---|
| 205/205 tests passing | **VERIFIED** | independently re-run: 205 passed, 0 skipped, 0 xfail; clean even under `-W error` [verified fact] |
| 37 golden / 69 security / 4 GUI tests | **VERIFIED** | `-m golden`=37, `-m security`=69 re-executed [verified fact] |
| ruff clean | **VERIFIED** | re-run clean [verified fact] |
| Licence gate passing + self-test | **VERIFIED** | re-run; self-test rejects 3/3 planted violations [verified fact] |
| Supported formats exactly V1 scope | **VERIFIED** | engine READABLE/WRITABLE sets inspected + runtime rejection of camt.052/.03 namespaces executed [verified fact] |
| Normalized-model architecture, no shortcuts | **VERIFIED** | all conversions route read→model→reconcile→write [static] |
| Decimal-only financial arithmetic | **VERIFIED** | zero `float(` hits in financial paths; mt940 lib uses Decimal; `ensure_decimal` rejects float [verified fact] |
| XSD validation of generated camt | **VERIFIED** | novel conversions validated in a SEPARATE environment (probe venv, Phase-0 XSD copies): v02 + v08 VALID [verified fact] |
| Reconciliation INV-1 arithmetic + honest mismatch reporting | **VERIFIED** | novel spot checks incl. overdraft crossing zero, RD/RC, 0.01 tamper → correct `difference` message; declared balances never "fixed" [verified fact] |
| GATE-1 both directions | **VERIFIED** | RD/RC ↔ CRDT/DBIT+RvslInd proven in reader+writer round trips with hand arithmetic [verified fact] |
| Offline operation | **VERIFIED** | zero network APIs in `src/`; hostile schemaLocation not fetched under socket block; `no_network=True` on lxml [verified fact] |
| GUI/CLI present and thin | **VERIFIED** | no business logic in `bfs_app`; save paths use sanitize+containment [static] |
| PyInstaller onedir build + installer exist | **VERIFIED** | dist 104 MB inspected to PYZ level (clean bundle: no fixtures/.git/dev packages); setup exe 33,017,337 bytes [verified fact] |
| Dependency versions vs dossier | **VERIFIED** | pip list matches DEPENDENCY-EVALUATION.md exactly [verified fact] |
| Bundled XSDs unmodified with recorded hashes | **VERIFIED** | SHA256 of bundled == references == SOURCE-PROVENANCE §B.1; generator comments intact [verified fact] |
| "Every dropped/truncated field produces a loss note" | **CONTRADICTED** | see B-1, C-2..C-5 — multiple silent-loss paths and one provably false loss note [verified fact] |
| "XLSX conservation verified via shared CSV projection" | **PARTIALLY VERIFIED → overstated** | engine returns `conservation_verified=True` for XLSX without reparsing anything (B-2/C-6) [verified fact] |
| Unsigned binaries | **VERIFIED** (and blocking for public release) | no signature on exe/installer; hooks honest [verified fact] |

## B. RELEASE BLOCKERS (must fix before selling)

**Engineering blockers:**

1. **B-1 — False information-loss note with real data loss (MT940 writer references).**
   `src/bfs_core/mt940/writer.py` `_ref16`/`_build_86`: notes claim "full value kept
   in :86:" but only the FIRST spilled value is written, and only when no
   `end_to_end_id` exists; a long `bank_reference` is truncated and its full value
   written nowhere while the report asserts it was preserved. The loss report —
   the product's core audit promise — is provably false for financial reference
   data. [verified fact, executed]
2. **B-2 — Duplicate statement IDs break CSV conversion of lawful real-world files.**
   `csvio/reader.py` keys statements by `statement_id`; two statements sharing one
   `:20:` (banks reuse these — the public ASNB fixture has 31 statements with the
   SAME `:20:0000000000`) → mt940→csv aborts with `E_INTERNAL "INV-7 conservation
   violated"`. The reparse net catches it (not silent), but a legitimate input
   class fails and is misreported as a product bug. [verified fact]
3. **B-3 — camt entries lacking both ValDt and BookgDt get a fabricated 1970-01-01
   value date with zero diagnostics**, which becomes 2070-01-01 after an MT940
   round trip (two-digit-year window). Schema-valid inputs can trigger it.
   `camt/reader.py` (`effective_value = ... or date(1970,1,1)`). [verified fact]

**Release-process blockers (owner-dependent):**

4. **B-4 — Unsigned binaries** (suitable for private testing only; commercial public release requires signing). Hooks exist, honestly unfilled. [verified fact]
5. **B-5 — Publisher placeholder `OWNER-LEGAL-ENTITY-NAME` is baked into the built installer's CompanyName**; rebuild required after setting it (`packaging/installer.iss:9`). [verified fact]
6. **B-6 — No EULA anywhere** (no licence text shown at install; `pyproject` says only "Proprietary"). A commercial proprietary product with no licence agreement is a legal gap. [verified fact / needs owner-legal]
7. **B-7 — Empty EXE version resource + no icon** (`packaging/bfs.spec` `version=None`, `icon=None`) — worsens SmartScreen/AV heuristics and looks unfinished. [verified fact]

## C. HIGH-PRIORITY FIXES (strongly recommended before public release)

1. **C-1** camt.053.001.02 batch details: per-detail debit/credit direction silently destroyed on write (no CdtDbtInd slot used, comment says "documented loss" but NO loss note emitted); reread flips a debit detail to credit; downstream CSV rows would carry wrong signs. Entry-level totals stay correct. (`camt/writer.py` batch path) [verified fact]
2. **C-2** Systematic silent field drops without loss notes: model→MT940 (`entry_reference`, `exchange_rate`, statement `additional_info`, `electronic_seq_number`, `from/to/creation datetime`, `btc` when `swift_tx_type` set, dangling `:60M:`→`:60F:` flattening); model→CSV (`return_reason` — reader even hard-codes None, `counterparty.is_agent`, `related_reference`, `additional_info`, others); model→camt.08 (`sequence_number` dropped, `StmtPgntn` hard-coded PgNb=1 — GATE-3 note exists only for .02). [verified fact]
3. **C-3** camt writer truncates many fields to schema lengths (`[:35]`, `[:140]`, `[:500]`) with no diagnostics; MT940 writer same for `related_reference[:16]`, `account[:35]`, `supplementary_details[:34]`. [static + executed for EndToEndId]
4. **C-4** MT940 15d amount length unenforced on write (16-char amount emitted for 15-digit+decimals values, invalid SWIFT, no diagnostic); the strict `parse_swift_amount` is dead code on the read path. [verified fact]
5. **C-5** PII masking backstop gap: `mask_value` `\b` anchoring misses account numbers embedded in adjacent text. Primary control (no value logging) holds; the backstop should too, for a privacy-marketed product. (`security/redact.py`) [verified fact]
6. **C-6** XLSX `conservation_verified=True` without any verification — either reparse the intermediate CSV pair or stop setting the flag. (`convert/engine.py`) [verified fact]
7. **C-7** THIRD-PARTY-NOTICES over-lists NON-shipped packages as "bundled" — including PyInstaller "GPLv2" — inviting licensing questions; PYZ inspection proves they are not bundled. (`generate_notices.py` skips only DEV_ONLY/FIRST_PARTY.) [verified fact]
8. **C-8** No customer-facing CSV dialect documentation ships — the "own documented dialect" promise is satisfied only by an internal spec; import rejects everything else, so customers need the column contract. [verified fact]
9. **C-9** `pytest-qt` undeclared in pyproject (GUI tests silently skip on fresh machines); venv pytest 9.1.1 contradicts the `pytest==8.*` pin; PyInstaller/ruff unpinned; no build-deps lockfile → build not reproducible to standard. [verified fact]
10. **C-10** README.md still says "PHASE 0 … No product code exists yet" while shipping 1.0.0. [verified fact]
11. **C-11** CI not enforced: workflow parked in `ci/` (valid-looking), `.github/workflows/` empty; GUI tests additionally run on NO CI leg. Restore before commercial release. [verified fact]
12. **C-12** Untested error branches: `E_CSV_INCONSISTENT` (3 raise sites, zero tests), `E_CSV_BAD_VALUE`/`E_CSV_MISSING_COLUMN` unasserted, `W_ENCODING_FALLBACK` untested, `E_ENCODING_UNDECODABLE` is dead code. [verified fact]

## D. ACCEPTED V1 LIMITATIONS (valid, non-blocking)

- XLSX import out of scope (locked decision); export-only verified.
- Golden-output residual circularity limited to element-mapping semantics; substantially mitigated by hand-authored inputs/figures (generation fails on disagreement — demonstrated), official-XSD validation, INV-7 reparse, and 16 public real-world files. [verified fact]
- Socket-blocking harness is Python-level; libxml2 C-level I/O is instead closed by `no_network=True` — document that the parser flags are the primary control. [inference, verified mitigation]
- Temp-file `0o600` is a Windows no-op (honestly hedged; `%TEMP%` ACL applies); sweep-by-prefix could interfere across instances (module unused in production paths).
- Foreign-currency booked entries toward MT940 are refused (correct, documented); non-BOOK entries dropped with loss note.
- INV-2 enforced stricter than spec (exact currency equality; SWIFT 3rd-char rule unimplemented) — may flag rare legitimate files.
- `.08` evidence thinner than `.02` (one public sample, no .08-input golden); reconciliation runs on merged chains (per-page equality enforced at merge).
- Internal `bfs_cli` exceeds the literal scope list but adds no format capability.
- `raw_86` audit-only, never re-emitted (documented).
- Qt6Network.dll ships unused (~2 MB; optics only). Minor falsy-Decimal edges (`net_amount==0` dropped from summary; zero-amount batch detail disables E13 sum check).

## E. OWNER ACTIONS (only items Claude cannot legitimately complete)

1. Code-signing identity (Trusted Signing or OV cert) and executing the signing hooks (B-4).
2. Legal entity name for `AppPublisher` (B-5) and EULA text / legal review (B-6).
3. Product icon asset (B-7, with version resource being an engineering fix).
4. Owner-legal confirmation of ISO 20022/SWIFT schema redistribution terms for a commercial product (notices wording is present and reasonable; classification: NEEDS OWNER/LEGAL REVIEW).
5. Clean-VM manual test execution (checklist in §K).
6. iso20022.org browser re-download hash confirmation (Phase-0 carry-over): **no evidence it was performed** — bundled hashes match the recorded Wayback-capture hashes [verified fact], so classified **RECOMMENDED BEFORE RELEASE**, non-blocking.
7. Restore CI workflow with credentials holding `workflow` scope (C-11 — the move itself is one command, but the push needs owner credentials).
8. VirusTotal scan + SmartScreen soft-launch plan; marketplace listing (future phase).

## F. OPTIONAL POST-V1 IMPROVEMENTS

Filter Qt6Network.dll from the bundle; nested-zip recursive scanning; "did you mean .08?" hint for version-shape mismatches; per-page reconciliation reporting; SWIFT 3rd-char currency rule; notices generator diffing against the actual PyInstaller graph; licence-gate hardening (allowlist substring `"mit"` over-matches; name-keyed exceptions unverified against licence changes; gate audits venv not bundle); GUI file-dialog path tests; user-visible support/contact channel in About.

## G. REQUIREMENT STATUS

**INV:** INV-1 VERIFIED · INV-2 PARTIAL (stricter than spec) · INV-3 PARTIAL ·
INV-4 VERIFIED · INV-5 VERIFIED · INV-6 VERIFIED · INV-7 PARTIAL (real reparse
for mt940/camt/csv; **asserted-not-verified for XLSX**, C-6) · INV-8 PARTIAL
(quantities conserved; field-loss reporting incomplete/false — B-1, C-1..C-3).

**E:** E1 ✓ · E2 PARTIAL (no separate per-page reconcile) · E3 ✓ · E4 ✓ · E5 ✓
(PRCD duplication nit) · E6 ✓ · E7 ✓ · E8 ✓ · E9 ✓ · E10 ✓ · E11 ✓ · E12 ✓ ·
E13 PARTIAL (C-1; zero-amount edge) · E14 PARTIAL (exactness ✓; 15d length
unenforced, C-4).

**GATE:** GATE-1 VERIFIED · GATE-2 VERIFIED · GATE-3 PARTIAL (.08 pagination
hard-coded, sequence dropped silently — C-2) · GATE-4 VERIFIED.

**SEC-01..24:** 01 PASS · 02 PASS · 03 PASS · 04 PASS · 05 MANUAL(future phase) ·
06 PASS · 07 PARTIAL (Windows chmod no-op, honestly hedged; sweep design) ·
08 PASS · 09 MANUAL(n/a — no recents list) · 10 PASS · 11 PASS w/ C-5 backstop gap ·
12 MANUAL (verify export wording) · 13 PASS · 14 PASS · 15 PASS · 16 PASS ·
17 PASS · 18 PASS · 19 MANUAL(owner) · 20 PARTIAL (runtime lock hashed; build
deps not — C-9) · 21 PASS · 22 PASS (installer per-user; verify on clean VM) ·
23 PASS · 24 PASS.

## H. TEST CONFIDENCE (by subsystem)

MT940 **HIGH** · camt .02 **HIGH** · camt .08 **MEDIUM** · CSV **MEDIUM**
(error branches untested — C-12) · XLSX **MEDIUM-HIGH** · reconciliation
**HIGH** · security **HIGH** · GUI **MEDIUM** (wiring only) · packaging **LOW**
(no automated tests exercise the frozen build).

## I. LICENCE/REDISTRIBUTION STATUS

- mt-940, lxml, xmlschema, elementpath, openpyxl, et_xmlfile (BSD/MIT), defusedxml (PSF): **CLEAR FOR TECHNICAL RELEASE**.
- PySide6/shiboken6/Qt LGPL-3.0: **CONDITIONALLY ACCEPTABLE — conditions met in the installed product** (DLLs replaceable [verified in dist], LGPL+GPL texts installed via installer, relink instructions + source pointers in notices, About notice). Caveat: the raw `dist/` folder alone lacks the licence texts — never distribute it as a bare zip without `licenses/`.
- PyInstaller (GPL-2.0+ w/ Bootloader Exception, build-only): **CONDITIONALLY ACCEPTABLE**; fix the notices mislisting (C-7).
- ISO 20022/SWIFT XSDs: **NEEDS OWNER/LEGAL REVIEW** (technical compliance in place).
- Product's own licence: **BLOCKER** until an EULA exists (B-6).
- Licence gate: sound for this dependency set, not adversary-proof (see F).

## J. PACKAGING STATUS

Build artefacts verified: onedir dist 104 MB (clean to PYZ level — no fixtures,
no dev packages, no VCS metadata; schemas + notices + btc data present; 5 Qt
DLLs as files); installer 31.5 MB, per-user, no elevation, offline, uninstall
via Inno. Defects: publisher placeholder in binary (B-5), empty version
resource/icon (B-7), fake-GUID AppId (cosmetic), no `UninstallDisplayIcon`, no
`LicenseFile` (pending EULA), licences only installed — absent from raw dist.
Reproducibility: **PARTIAL** — runtime deps hash-locked; PySide6/PyInstaller/
pytest-qt/ruff unpinned or undeclared; build interpreter (3.14) undocumented;
build.ps1 lacks a bootstrap step (C-9).

## K. CLEAN-VM TEST CHECKLIST (for the owner — not performed in this audit)

On a clean Windows 10 or 11 VM, **standard (non-admin) account**, snapshot first:
1. Disable networking (airplane mode / remove adapter). Copy the installer in via ISO/shared folder.
2. Run `BankFormatStudio-1.0.0-setup.exe`. Record any SmartScreen/Defender prompts verbatim (screenshots). Confirm NO elevation prompt appears and install completes offline.
3. Confirm install landed under `%LOCALAPPDATA%\Programs\Bank Statement Format Studio` with `THIRD-PARTY-NOTICES.txt` and `licenses\LICENSE.LGPL3.txt`/`LICENSE.GPL3.txt` present.
4. Launch. Confirm the About dialog (version, offline statement, LGPL notice).
5. Convert a synthetic MT940 (e.g. repo `tests/fixtures/mt940/M01.sta` copied over) → camt.053.001.02: preview renders, reconciliation shows RECONCILED, save both output and verify the file opens in a text editor.
6. Repeat: camt .02 input → CSV (confirm BOTH transactions.csv + statements.csv written); camt .08 input → MT940; CSV pair input → camt; MT940 → XLSX (open in Excel: `=`-prefixed text shows apostrophe-guarded, amounts are numbers).
7. Feed a malformed file (M06-style) and a wrong-balance file (M11-style): confirm human-readable errors/mismatch — no crash, no hang.
8. Task Manager → confirm no network activity; optionally run with firewall in block-all-and-log mode and confirm zero connection attempts.
9. Uninstall via Settings → Apps. Confirm program folder removed; check `%TEMP%\bank-format-studio` and `%LOCALAPPDATA%` for residues.
10. Re-enable networking only after the VM is reverted.

## L. EXACT FILES REQUIRING CHANGES (issue only — NOT changed in this audit)

| File | Issue |
|---|---|
| `src/bfs_core/mt940/writer.py` | B-1 false spill note; C-2 silent drops; C-3 `related_reference[:16]` etc.; C-4 no 15d cap |
| `src/bfs_core/csvio/reader.py` | B-2 statement_id collision; C-12 untested branches; `return_reason=None` hard-code |
| `src/bfs_core/camt/reader.py` | B-3 1970-01-01 fabricated date, no diagnostic |
| `src/bfs_core/camt/writer.py` | C-1 .02 batch direction loss w/o note; C-2 .08 sequence drop; C-3 silent truncations |
| `src/bfs_core/convert/engine.py` | C-6 XLSX conservation flag asserted, not verified |
| `src/bfs_core/security/redact.py` | C-5 `\b`-anchored masks miss embedded tokens |
| `src/bfs_core/errors.py` | C-12 `E_ENCODING_UNDECODABLE` dead code |
| `packaging/installer.iss` | B-5 publisher; B-6 no LicenseFile; cosmetic AppId/UninstallDisplayIcon |
| `packaging/bfs.spec` | B-7 `version=None`, `icon=None` |
| `packaging/generate_notices.py` | C-7 over-listing non-shipped packages as bundled |
| `pyproject.toml` | C-9 pytest-qt undeclared; pyinstaller/ruff unpinned; pytest pin contradicted by venv |
| `README.md` | C-10 stale "Phase 0 / no product code" |
| `ci/github-workflow-ci.yml` (+ `.github/workflows/`) | C-11 not enforced; no GUI-test leg |
| (missing) customer-facing CSV dialect doc | C-8 |
| (missing) EULA file | B-6 |

## M. FINAL VERDICT

**AMBER — ENGINEERING READY, RELEASE ACTIONS/FIXES REQUIRED.**

The core is genuinely sound and was verified adversarially: exact Decimal
arithmetic end-to-end, correct sign/reversal semantics in all four
reader/writer paths, honest reconciliation that reports (never repairs)
mismatches, real offline guarantees, a clean bundle, and LGPL mechanics that
hold in the installed product. It is **not sellable today**: three engineering
blockers concentrate in the fidelity/loss-reporting layer (B-1 false loss note,
B-2 duplicate-ID failure on real-world files, B-3 fabricated dates) — precisely
the layer the product's honesty promise rests on — and four release-process
blockers (signing, publisher identity, EULA, exe metadata) remain. RED was
considered and rejected because the defects are localized, well-understood, and
the architecture/arithmetic verification passed everything thrown at it.

## N. NEXT ACTION — smallest ordered path to GREEN

1. Fix B-1 (write every spilled reference into `:86:` or make the note truthful) + B-3 (refuse or warn+note on missing camt dates; never fabricate) + B-2 (key CSV statements by ordinal or composite key). Add regression tests for each.
2. Fix C-1 (loss note + documented behaviour for .02 mixed-direction batches) and C-6 (actually reparse the XLSX CSV projection); sweep C-2/C-3 by adding the missing loss notes (mechanical; the reporting plumbing already exists) and C-4 (enforce 15d with an error).
3. Fix C-7 notices over-listing, C-9 pins (declare pytest-qt, pin pyinstaller/ruff, reconcile pytest, add a build lockfile), C-10 README, C-12 CSV error-branch tests + encoding fallback test; add the C-8 customer CSV dialect doc; C-5 mask regex.
4. Owner: EULA text (B-6), publisher name (B-5), icon (B-7 asset), then rebuild with exe version metadata (engineering completes B-7).
5. Owner: restore CI to `.github/workflows/` (C-11) and confirm green on GitHub.
6. Owner: obtain signing identity, sign exe + installer (B-4); rebuild/sign.
7. Owner: execute the §K clean-VM checklist and the VirusTotal scan; file results.
8. Re-run this audit's §B/§C verification set; if clear → **GREEN**.

---
*Audit complete. No repository files were modified; this report is the only artefact created.*
