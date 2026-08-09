# ENGINEERING REMEDIATION REPORT — Bank Statement Format Studio V1

Date: 2026-08-09. Directive: `temp/ENGINEERING-REMEDIATION-GOAL.md`; backlog:
`temp/FINAL-RELEASE-AUDIT.md`. Scope: engineering findings only — owner/release
actions (signing, EULA, identity, clean-VM, marketplaces) were NOT performed.

## 1. Original Findings (from FINAL-RELEASE-AUDIT.md)

Engineering: B-1 false loss note / lost references; B-2 duplicate statement-ID
CSV failure; B-3 fabricated 1970-01-01 dates; C-1 .02 batch direction
corruption; C-2 silent field drops (MT940/CSV/camt.08 writers); C-3 silent
truncations; C-4 unenforced 15d amount; C-5 PII-mask boundary gap; C-6 XLSX
conservation asserted-not-verified; C-7 notices over-listing; C-8 no customer
CSV dialect doc; C-9 undeclared/unpinned build deps; C-10 stale README; C-11 CI
unenforced/no GUI leg; C-12 untested CSV error branches + dead error code.
Owner-side (NOT engineering): B-4 signing, B-5 publisher identity, B-6 EULA,
B-7 icon (+ version resource, engineering-adjacent, see §14).

## 2. Fix Status

| Finding | Status | Files changed |
|---|---|---|
| B-1 | **FIXED** | `src/bfs_core/mt940/writer.py`, `mt940/profiles.py`, `mt940/reader.py`; tests `tests/unit/test_remediation.py::TestB1*`, `test_writers.py` |
| B-2 | **FIXED** | `csvio/dialect.py`, `csvio/writer.py`, `csvio/reader.py`; `TestB2*` (incl. the real 31-duplicate public ASNB file) |
| B-3 | **FIXED** | `camt/reader.py`, `errors.py` (`E_CAMT_MISSING_DATE`); `TestB3*` |
| C-1 | **FIXED** | `camt/writer.py` (mixed-direction .02 batches), `camt/reader.py` (sum-check guard); `TestC1*` |
| C-2 | **FIXED** | `mt940/writer.py`, `csvio/writer.py`, `camt/writer.py` (+ GATE-3 .08 `StmtPgntn`, `:60M:` preservation, `/OCMT//EXCH/` round-trip); `TestC2*` |
| C-3 | **FIXED** | `camt/writer.py` `_el_fit` truncation diagnostics; `mt940/writer.py` (:21:/:25:/supplementary); `TestC2*` |
| C-4 | **FIXED** | `model/money.py` 15d enforcement; `TestC4*` |
| C-5 | **FIXED** | `security/redact.py`; `TestC5*` |
| C-6 | **FIXED** | `convert/engine.py` `_verify_xlsx_conservation`; `TestC6*` |
| C-7 | **FIXED** | `packaging/generate_notices.py` (build-tools section), `tools/licence_gate.py` DEV_ONLY |
| C-8 | **FIXED** | `docs/CSV-DIALECT.md` (new, shipped via `packaging/installer.iss`) |
| C-9 | **FIXED** | `pyproject.toml` (pytest-qt declared, pytest==9.*, ruff/pyinstaller bounded), `requirements-build.in`/`.lock` (hash-pinned), README build-interpreter note |
| C-10 | **FIXED** | `README.md` rewritten |
| C-11 | **FIXED** (workflow content) / **OWNER ACTION** (restore to `.github/workflows`) | `ci/github-workflow-ci.yml` (golden step, GUI job, warnings-as-errors via pyproject) |
| C-12 | **FIXED** | CSV error-branch tests (`TestC12*`), encoding-fallback test, dead `E_ENCODING_UNDECODABLE` removed from `errors.py` |
| B-4/B-5/B-6/B-7 | **OWNER ACTION** | untouched by design (no fabricated signing/identity/EULA) |

## 3. B-1 Evidence

`:61:` subfields still truncate to 16x (format constraint), but every truncated
reference's FULL value is now written into `:86:` under a dedicated code word —
`/CREF/` for the customer reference, `/ASREF/` for the bank reference — added to
the documented output convention and to the reader's vocabulary, so reparse
restores the complete values. Multiple overflowing references are all written;
`/EREF/` coexists (the audit's proven failure case: both refs long + EndToEndId
present now yields `/EREF/…/CREF/…/ASREF/…`). The loss note now states "full
value written to :86: as /CREF/" — verified truthful by regression tests and
independent probe P1. Deterministic generation preserved (fixed word order).

## 4. B-2 Evidence

CSV dialect v1.1: a DERIVED `statement_occurrence` column (1-based per-id
ordinal, explicitly documented as a file-local disambiguator, not bank data) in
both transactions.csv and statements.csv. The reader keys statements by
(statement_id, occurrence); transaction rows carry the same pair. Backward
compatibility: v1.0 files without the column remain readable while ids are
unique (ordinal fallback); files with duplicate ids and no occurrence column
are rejected with `E_CSV_INCONSISTENT` naming the missing column — never
`E_INTERNAL`. Round trip preserves statement count/order and conservation keys.
Real-world regression: the public ASNB fixture (31 statements sharing
`:20:0000000000`, BSD-licensed) now converts mt940→csv→mt940 with conservation
verified (test + probe P2).

## 5. B-3 Evidence

`camt/reader.py` never invents dates: ValDt is used when present; BookgDt-only
entries use BookgDt with an explicit DERIVED loss note; entries with neither
raise stable `E_CAMT_MISSING_DATE`. Regression tests cover all four
combinations and prove no 1970/2070 artefact can be produced (probe P3).

## 6. Fidelity Sweep

Silent paths found and treated (all now diagnose): MT940 writer — entry_reference
(DROPPED note), structured BTC beside a SWIFT code (FLATTENED note), statement
additional_info / electronic_seq_number / timestamps (DROPPED notes),
`:21:`+`:25:`+supplementary truncations (TRUNCATED notes + :21: transliteration),
dangling `:60M:` now written as `:60M:` (behaviour fix, loss eliminated),
exchange_rate now WRITTEN as `/EXCH/` and OCMT/EXCH parsed back into the model
(loss eliminated). CSV writer — return_reason, agent flag, btc issuer,
related_reference, statement additional info, electronic seq, timestamps
(DROPPED notes); per-statement `information_loss_flags` now scoped to that
statement. camt writer — every schema-length cut (`Id`, EndToEndId, InstrId,
MndtId, AcctSvcrRef, NtryRef, CdtrRef, Nm, AddtlNtryInf/StmtInf, Othr/Id,
Purp/RtrInf codes) diagnosed via `_el_fit`; .08 `StmtPgntn/PgNb` now carries the
MT940 page number (GATE-3 loss eliminated). camt.02 mixed-direction batches: per-
detail amounts omitted (schema cannot carry direction) with a DROPPED note —
sign corruption eliminated; same-direction batches unchanged; aggregate
arithmetic unaffected (probe P4).

## 7. Security Fixes

`mask_value` anchors removed: embedded IBANs/long numbers in concatenated text,
JSON-like strings and path fragments are masked (adversarial tests + probe P6:
`stmtNL91ABNA0417164300.sta`, `refDE75…end`, `acct00998877665544` all masked;
short tokens like "row 42" untouched). All prior SEC logging tests still pass.

## 8. XLSX Verification

`conservation_verified=True` for XLSX now means: (a) the strict CSV projection
the workbook is built from was reparsed and every statement's conservation key
matched, AND (b) the produced workbook was opened (internal check only — XLSX
import remains outside V1) and per-(statement_id, occurrence) row counts and
signed amount sums matched the normalized statements. A tampered workbook cell
is detected (test + probe P7 both raise on a 1-cent-class change).

## 9. Tests

- Previous count: **205 passed**. New count: **248 passed, 0 failed, 0 skipped,
  0 xfail** (43 added; 1 existing test updated because it asserted the defective
  B-1 behaviour — now asserts full-reference round-trip, justified in-code).
- Golden: 37 (35 cases + 2 INV-8 round trips). Security: 69. GUI: 4.
- Warnings: `filterwarnings = ["error"]` now enforced via pyproject; full suite
  clean under it.
- Lint: ruff clean (src, tests, tools, packaging). Licence gate: self-test 3/3
  rejections; environment audit passed (15 shipped-candidate distributions).
- Goldens were regenerated ONCE for documented fidelity reasons (B-1 spill
  format, B-2 occurrence column, C-1/C-2/C-3 loss-note and output changes) —
  log embedded in `tools/gen_fixtures.py`; authored-figure cross-checks and
  XSD self-validation re-ran at freeze time.

## 10. Independent Probe Results (all novel inputs; all PASS)

P1 both-long references + EndToEndId → full values round-trip. P2 three
duplicate statement ids → csv → mt940, conservation verified, 3 statements.
P3 dateless camt entry → `E_CAMT_MISSING_DATE`. P4 .02 mixed batch → no
fabricated signs, loss note present, no spurious batch-sum warning.
P5 16-char amount → `E_MT940_BAD_AMOUNT`. P6 embedded account tokens masked.
P7 tampered workbook detected by the real verifier.

## 11. Requirement Status (re-evaluated post-remediation)

INV-1..6 PASS (unchanged, suite re-run) · INV-7 **PASS** (now including real
XLSX verification) · INV-8 **PASS** (loss reporting corrected: previously
PARTIAL for false/missing notes).
E1..E12 PASS · E13 **PASS** (.02 direction corruption eliminated; zero-amount
guard corrected) · E14 **PASS** (15d enforced both ways of the boundary).
GATE-1/2/4 PASS · GATE-3 **PASS** (.08 pagination now carries the page number).
SEC-01..24: unchanged verdicts except SEC-11 backstop gap → **PASS** (C-5).
SEC-05/09/12/19/22 remain MANUAL/owner-side as before; SEC-07 PARTIAL
(documented Windows ACL semantics) unchanged and accepted.

## 12. Licensing/Dependency Status

No new runtime dependencies. Dev/build tooling now declared and hash-pinned
(`requirements-build.lock`: pytest 9.1.1, pytest-qt 4.5.0, ruff 0.16.2,
pyinstaller 6.22.0, PySide6-Essentials 6.11.1, pip-licenses 5.5.5 + hashes).
THIRD-PARTY-NOTICES now separates BUILD TOOLS (not distributed) from bundled
components, with the PyInstaller Bootloader Exception statement. Unresolved
review items (unchanged, owner/legal): ISO 20022/SWIFT schema redistribution
confirmation; product EULA.

## 13. Build Status

Post-remediation rebuild via `packaging/build.ps1` (full pipeline: licence gate
→ 248-test suite → notices → licence texts → PyInstaller `--onedir` → Qt-DLL
relink check → Inno Setup): **SUCCESS**. Fresh
`packaging/Output/BankFormatStudio-1.0.0-setup.exe` (33,019,108 bytes,
2026-08-09 18:01); bundled schemas verified present in the dist; CSV-DIALECT.md
added to the installer payload; frozen application startup smoke **PASSED**
(process alive at 8 s, terminated cleanly). Binaries remain **UNSIGNED** —
owner action, not fabricated.

## 14. Remaining Engineering Defects

None known at severity above "accepted limitation". Accepted limitations
carried forward, documented: Windows `0o600` semantics (`tempfiles.py`),
sweep-by-prefix design (module unused in product paths), nested-zip
non-recursion (no xlsx import), golden element-mapping residual circularity
(mitigated as audited), `.08` public-sample evidence thinner than `.02`,
`resolve_inside` containment-only (callers sanitize first), EXE version
resource/icon pending owner assets (B-7: the version-resource half is
engineering but needs the owner's publisher/copyright strings to fill in — kept
with B-5/B-7 to avoid inventing identity).

## 15. Owner/Release Actions Remaining

Unchanged from the audit: code signing (B-4); publisher legal name in
`installer.iss` + rebuild (B-5); EULA (B-6); icon + version-resource strings
(B-7); restore CI workflow to `.github/workflows/` with `workflow`-scoped
credentials; clean-VM test (checklist in FINAL-RELEASE-AUDIT §K); VirusTotal;
ISO 20022 redistribution legal confirmation; iso20022.org browser hash
re-check (recommended).

## 16. Git Status

Remediation commits: `b6f0b19` (1/3 fidelity blockers + sweep + goldens),
`f5a3d05` (2/3 PII masking), `62e9416` (3/3 release-quality), plus a final
build/report commit (hash in `git log`). Pushed to
`https://github.com/leelaravind/bank-format-studio.git` `main`. No history
rewrites, no force-pushes.

## 17. ENGINEERING VERDICT

**GREEN — ENGINEERING READY FOR RELEASE PREPARATION.**

All locally achievable engineering blockers and high-priority findings from the
independent audit are corrected and independently re-verified (248/248 tests,
warnings-as-errors, lint, licence gate, 7 novel probes, rebuilt artifacts).
GREEN does not mean commercially released: the owner actions in §15 —
signing, identity, EULA, CI restoration, clean-VM validation — remain
prerequisites for actual distribution.
