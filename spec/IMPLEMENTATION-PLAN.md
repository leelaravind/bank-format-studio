# IMPLEMENTATION PLAN — Bank Statement Format Studio V1

Phase 1 deliverable. Date: 2026-08-09. Plan only — no product code exists yet.
Scope authority: spec/V1-SCOPE-RECOMMENDATION.md (Option C with guardrails).
This plan resolves the four open technical gates from spec/DATA-MAPPING-RESEARCH.md §3
and the four deferred CSV decisions from spec/CSV-FORMAT-STRATEGY.md §6, and traces
every INV-1..8, E1..E14 and SEC-01..24 requirement into planned tests.

---

## 1. Resolution of the four open technical gates

### GATE-1 — `:61:` D/C mark value set → RESOLVED: `{C, D, RC, RD}`

Evidence: Rabobank MT940S spec and kontopruef.de (independent references collected in
Phase 0) agree on C/D/RC/RD; the approved `mt-940` 5.0.0 parser accepts exactly the
pattern `R?[DC]` (observed directly in Probe 1 diagnostics); no collected public
reference places `EC`/`ED` in `:61:` subfield 3 — expected-entry marks belong to
interim-report (MT942-family) contexts, not the customer statement.

Decisions:
- Parser accepts `C`, `D`, `RC`, `RD` only; anything else → error `E_MT940_BAD_DC_MARK`
  with a human-readable message naming the offending line.
- Mapping (both directions, per RECONCILIATION-REQUIREMENTS.md §1):
  `C ↔ CRDT` (no RvslInd), `D ↔ DBIT` (no RvslInd),
  `RD ↔ CRDT + RvslInd=true`, `RC ↔ DBIT + RvslInd=true`.
- `RvslInd` is confirmed present as an optional `Ntry` element in **both** V1 schema
  targets (camt.053.001.02.xsd line 1029; camt.053.001.08.xsd line 1668), so the
  mapping is representable without loss in both directions. Tests: T-E03, T-GATE1.

### GATE-2 — camt .02 vs .08 model-affecting differences → RESOLVED (enumerated)

Verified directly against the bundled XSDs:

| Difference | .001.02 | .001.08 | Consequence |
|---|---|---|---|
| Reversal indicator | `RvslInd` optional | `RvslInd` optional | identical mapping, no adapter needed |
| Related parties | `Cdtr`/`Dbtr` : `PartyIdentification32` (direct) | `Party40Choice` (`Pty` \| `Agt`) | version adapters unwrap/wrap; normalized model stores counterparty struct + `is_agent` flag |
| Statement pagination | none | `StmtPgntn` (`Pagination1`: PgNb, LastPgInd) | drives GATE-3 mapping |
| Balance type codes | **closed enum** `BalanceType12Code` = {XPCD, OPAV, ITAV, CLAV, FWAV, CLBD, ITBD, OPBD, PRCD, INFO} | **external code set** `ExternalBalanceType1Code` (pattern string) | version-aware code validation; unknown .08 codes carried through with WARNING, never invented on write |
| Transactions summary | `TotalTransactions2` (`TtlNetNtryAmt` decimal + separate CdtDbtInd) | `TotalTransactions6` (`TtlNetNtry` : `AmountAndDirection35`) | INV-5 checker gets per-version adapters |

Architecture consequence: the normalized model is version-neutral; all differences are
absorbed in thin per-version reader/writer adapters at the XML boundary (§3.2).
Tests: T-GATE2 (adapter unit tests per row above), T-E05.

### GATE-3 — `:28C:` ↔ camt sequence mapping → RESOLVED

- MT940 statement number (before `/`) ↔ `LglSeqNb` (optional `Number`, both versions —
  XSD-verified).
- MT940 page number (after `/`) ↔ **.08**: `StmtPgntn/PgNb` + `LastPgInd`;
  **.02**: no slot — pages are merged into one `Stmt` on conversion, original page
  count recorded in the information-loss report and `AddtlStmtInf`.
- `ElctrncSeqNb`: on generation, set equal to the statement number unless the source
  camt provides its own; on camt→MT940, `:28C:` statement number resolution order is
  `LglSeqNb` → `ElctrncSeqNb` → `1`, with a loss note whenever both are present and
  differ (28C carries only one number). Tests: T-GATE3, T-E02, T-E12.

### GATE-4 — V1 structured `:86:` output convention → RESOLVED: SWIFT slash code words

camt→MT940 output writes `:86:` in the slash code-word convention (the
Dutch/Rabobank-documented family): `/EREF/`, `/PREF/`, `/MARF/`, `/CSID/`,
`/ORDP/` or `/BENM/` with nested `/NAME/` `/ID/`, `/REMI/`, `/PURP//CD/`, `/RTRN/`,
`/ULTD/`, `/ULTB/`, `/ISDT/`.

Rationale: (a) near-1:1 mapping from camt structured elements; (b) fully documented in
the legally accessible references collected in Phase 0 (no proprietary dependency);
(c) SWIFT X-charset-safe; (d) parseable back by our own reader, enabling round-trip
golden cases. German GVC `?nn` output is **rejected** for V1: it requires a GVC
business-code table whose authoritative sources are DK-specific with unverified reuse
terms. GVC remains **input-side only** (read via variant profile). One output
convention, documented in the product manual. Tests: T-GATE4, golden pairs G-C0x-MT940.

## 2. Resolution of deferred CSV decisions (CSV-FORMAT-STRATEGY.md §6)

1. **NONREF**: passed through verbatim in `customer_reference`; empty cell means
   "absent". Rationale: determinism and reversibility — normalizing erases the
   distinction between "no reference" and the literal `NONREF` token.
2. **XLSX export** = straight rendering of the same two tables as worksheets
   (`transactions`, `statements`), same columns, native number/date cells. No
   formatted report sheet in V1.
3. **Column naming**: `snake_case` confirmed (as specified in §3/§4 of the strategy).
4. **statements.csv**: mandatory on every export (deterministic pairing; the
   reconciliation summary must always accompany transaction rows). No single-file
   mode in V1.

---

## 3. Architecture

### 3.1 Package layout (future; nothing created yet)

```
src/bfs_core/                # pure library — no GUI imports, no network, no I/O side effects
  model/                     # normalized model: Statement, Balance, Transaction,
                             #   Counterparty, Diagnostics (Decimal-exact, version-neutral)
  mt940/
    reader.py                # wraps mt-940 lib; envelope strip; encoding detection
    profiles.py              # variant profiles: default, nl_structured, de_gvc, tolerant
    writer.py                # single output convention (GATE-4)
  camt/
    versions.py              # namespace detection incl. unsupported-version errors
    reader_v02.py/reader_v08.py  # thin adapters (GATE-2) over shared core reader
    writer_v02.py/writer_v08.py
    validate.py              # xmlschema wrapper → structured, translatable errors
    schemas/                 # bundled XSDs (from references/camt053, unmodified)
  csvio/                     # own-dialect reader/writer (RFC 4180, BOM, CRLF)
  xlsx/                      # openpyxl writer (V1); reader behind a feature flag (stretch)
  reconcile/                 # INV-1..8 engine; per-version TxsSummry adapters
  convert/
    engine.py                # any→model→any orchestration
    loss.py                  # information-loss report (typed entries)
    btc_map.py               # SWIFT 4-char ↔ BTC domain/family best-effort table (data file)
  errors.py                  # stable error/warning codes (E_*, W_*) + message catalog
  security/                  # path sanitization, temp-file lifecycle, size limits
src/bfs_app/                 # PySide6 GUI (thin: file pickers, preview tables, reports)
src/bfs_cli/                 # internal CLI (drives core for tests/CI; not a marketed feature)
tests/
  unit/  integration/  golden/  security/  fixtures/
packaging/                   # PyInstaller spec, Inno Setup script, THIRD-PARTY-NOTICES build
```

### 3.2 Data flow

Every conversion: `input file → format reader → NormalizedStatement[] + Diagnostics →
reconcile (INV-1..8) → format writer → output + reconciliation report + loss report`.
Readers never guess silently: every heuristic (entry-date year, encoding, variant
detection) emits a diagnostic. Writers are deterministic (fixed ordering, pinned
formatting, injected clock).

### 3.3 Key design rules (binding)

- `decimal.Decimal` everywhere; construction from `float` is forbidden (lint rule).
- Normalized model is the only bridge; no format-to-format shortcuts.
- All parsers hardened per SEC-13/14/15; all file writes route through `security/paths.py`.
- Error codes are stable API (GOLDEN-CASE-REQUIREMENTS.md rule 6).
- Every dropped/truncated/transliterated/derived field goes through `convert/loss.py` —
  no silent loss (enforced by golden rule 4).

## 4. Milestones

| # | Milestone | Contents | Exit criteria |
|---|---|---|---|
| P1-M0 | Scaffolding | pyproject (pinned, hashed deps), CI (Windows, py 3.12–3.14), pip-licenses gate (block GPL/AGPL), lint, THIRD-PARTY-NOTICES generator | CI green on empty package; licence gate proves it fails on a planted GPL dep |
| P1-M1 | Normalized model + diagnostics | model/, errors.py, loss-report types | unit tests; JSON serialization for golden `normalized.json` |
| P1-M2 | MT940 reader | envelope/encoding handling, variant profiles, `mt-940` integration | fixtures M01–M20 + all 9 public fixtures parse with expected diagnostics |
| P1-M3 | camt readers + validation | versions.py, v02/v08 adapters, xmlschema validation, error translation | fixtures C01–C14 + all 7 public samples; GATE-2 adapter tests |
| P1-M4 | Reconciliation engine | INV-1..8, per-version summary adapters | T-INV-1..8, T-E01..E14 (arithmetic subset) green |
| P1-M5 | Writers | camt v02/v08, MT940 (GATE-4 convention), CSV dialect, XLSX export | outputs XSD-validate / re-parse; determinism test (byte-identical double run) |
| P1-M6 | Conversion engine + goldens | engine, loss reports, BTC map; author synthetic fixture set (FIXTURE-PLAN) + ~45 golden cases | all goldens green incl. round-trip pairs; loss reports asserted |
| P1-M7 | Security hardening | security/, attack fixtures (XXE, zip bomb, traversal, injection), network guard | T-SEC suite green; conversion runs under a socket-blocking test harness |
| P1-M8 | GUI | PySide6 app: open→preview→convert→reports→save; masked logging | manual test script + automated smoke via pytest-qt |
| P1-M9 | Packaging | PyInstaller --onedir, Inno Setup, signing hook, LGPL compliance items | installed app passes smoke on clean Win10/11 VM, offline; compliance checklist done |
| P1-M10 | Release readiness | docs, EULA, VirusTotal scan, SmartScreen plan, Lemon Squeezy/Gumroad artefact | release checklist (§6) fully ticked |

Dependencies: M2/M3 parallelizable after M1; M4 needs M2+M3; M5 needs M1 (writers
test against M4 for self-consistency); M6 needs M2–M5; M7 spans M2–M6 outputs;
M8 needs M6; M9 needs M8.

## 5. Test plan and full requirement traceability

Test ID scheme: `T-INV-n`, `T-En`, `T-SEC-nn`, `T-GATEn`, `G-*` (golden cases).
Fixture IDs reference spec/FIXTURE-PLAN.md. **Every requirement below has at least
one planned verification; none are waived.**

### 5.1 Reconciliation invariants (RECONCILIATION-REQUIREMENTS.md)

| Req | Planned tests | Fixtures / method |
|---|---|---|
| INV-1 (opening + Σmovements = closing) | T-INV-1 unit (property-based: generated statements) + every VALID golden case asserts it | M01–M05, C01, C12; hypothesis-style generator |
| INV-2 (MT940 currency consistency) | T-INV-2 | M07 (invalid currency), M17 (`:64:`/`:65:` present), synthetic mismatch variant |
| INV-3 (camt currency consistency) | T-INV-3 | C11 (non-account currency + exchange), synthetic Ccy-mismatch |
| INV-4 (page chaining 62M→60M, 28C continuity) | T-INV-4 | M12 (valid chain) + synthetic broken-chain variant (from ABN AMRO public fixture pattern) |
| INV-5 (TxsSummry cross-check) | T-INV-5 (per-version adapters, GATE-2) | C02 (.02 and .08 renderings), synthetic wrong-sum variant |
| INV-6 (date sanity) | T-INV-6 | synthetic FrToDt-violation fixture; M20 (year boundary) |
| INV-7 (conversion conservation) | T-INV-7 asserted inside every golden conversion | all G-* cases |
| INV-8 (round-trip conservation + documented-loss-only diffs) | T-INV-8 | round-trip golden pairs (G-M0x↔G-C0x, V06) |

### 5.2 Edge cases E1–E14

| Req | Planned tests | Fixtures |
|---|---|---|
| E1 zero transactions | T-E01 | M05, C12 |
| E2 multi-page MT940 | T-E02 (+GATE-3 mapping) | M12 |
| E3 reversals | T-E03 (+GATE-1 mapping both directions) | M13, C07 |
| E4 overdraft / sign crossing | T-E04 | synthetic D-balance statement crossing zero |
| E5 multiple balance types | T-E05 (+GATE-2 code-set rules) | C04, M17; PRCD-substitution case |
| E6 non-BOOK status | T-E06 | C09 (PDNG excluded + warned; camt→MT940 refuses entry with loss note) |
| E7 duplicate entries | T-E07 | M10 (warning, arithmetic unaffected) |
| E8 balance currency mismatch | T-E08 | synthetic (hard error) |
| E9 decimal-places vs ISO 4217 | T-E09 | M19 (JPY), C05-adjacent 5-decimal sample (public CAMT-S05) |
| E10 declared ≠ computed closing | T-E10 | M11, C06 (FAIL_RECONCILIATION with human-readable diff) |
| E11 partial statement | T-E11 | M09 (hard error, no guessed balance) |
| E12 sequence gaps across files | T-E12 | synthetic 2-file batch with gap (WARNING) |
| E13 batch entries | T-E13 | C08 (Ntry = Σ TxDtls; CSV row-per-TxDtls grouping) |
| E14 15-digit amounts | T-E14 | M19; serializer no-scientific-notation assertion |

### 5.3 Security requirements SEC-01..24

| Req | Verification |
|---|---|
| SEC-01 offline function | T-SEC-01: full conversion suite runs inside a socket-blocking pytest fixture (monkeypatched `socket.socket` raises) |
| SEC-02 zero network in conversion paths | same harness as T-SEC-01 (any socket call fails the test); code review gate: no `requests/urllib/socket` imports in bfs_core (lint rule) |
| SEC-03 no telemetry/analytics | static check: dependency and import audit in CI (T-SEC-03); release checklist item |
| SEC-04 no data leaves machine | covered by SEC-01/02 harness + packaging review (installer offline test, P1-M9) |
| SEC-05 offline-capable licensing design | design-review checklist item in P1-M10 (activation is future phase; requirement recorded in EULA/design notes) |
| SEC-06 no shadow copies | T-SEC-06: filesystem-watcher test — convert run leaves zero files outside chosen output dir |
| SEC-07 temp-file lifecycle | T-SEC-07: unit tests on security/tempfiles (ACL flags, unpredictable names, cleanup incl. simulated-crash sweep on startup) |
| SEC-08 path traversal | T-SEC-08: property + table tests on security/paths (`..`, separators, CON/PRN/AUX/NUL/COM1../LPT1.., trailing dots/spaces, control chars); attack fixture set |
| SEC-09 recents = paths only | T-SEC-09: GUI unit test (settings file contains no file contents; clearable; disableable) |
| SEC-10 no PII at default log level | T-SEC-10: log-capture test over full conversion of PII-rich fixture asserts no account numbers/names/descriptions in records |
| SEC-11 masking in persisted logs | T-SEC-11: unit tests for masker (IBAN → `DE89…3000`); opt-in verbose path requires explicit flag + warning banner assertion |
| SEC-12 exported reports flagged sensitive | T-SEC-12: report generator output contains the sensitivity notice |
| SEC-13 XML hardening | T-SEC-13: attack fixtures — DTD present, external entity, billion-laughs, `schemaLocation` URL — all rejected with controlled errors; parser-config unit tests |
| SEC-14 untrusted-input robustness | T-SEC-14: fuzz-lite corpus (mutated M06/C05 + random truncations) must never crash/hang; resource caps asserted (M06, M09, C05, C13 + generated mutations) |
| SEC-15 xlsx zip safety | T-SEC-15: crafted zip-bomb and traversal-name xlsx fixtures rejected before extraction |
| SEC-16 CSV formula-injection guard on export | T-SEC-16: V02 fixture round-trip; Excel-safe vs strict-RFC mode matrix; numeric-cell exemption |
| SEC-17 CSV import never evaluates | T-SEC-17: import of V02 payloads yields inert strings (asserted) |
| SEC-18 deterministic encoding rules | T-SEC-18: fixture matrix (BOM/no-BOM, declared XML encoding, CP1250/CP1252 MT940 bytes — public fixtures M-S08/S09) resolves per documented priority |
| SEC-19 signed binaries | release checklist P1-M9/M10 (signtool verify step in CI release job) |
| SEC-20 pinned+hashed deps, licence CI gate | P1-M0 exit criteria; T-SEC-20: CI job proves `--require-hashes` install and licence gate failure on planted GPL dep |
| SEC-21 no auto-update | static/dependency audit (same job as SEC-03); release checklist |
| SEC-22 per-user install, no elevation | P1-M9: Inno Setup config review + install test on non-admin VM account |
| SEC-23 honest memory/disk claims | documentation review checklist item (marketing/docs sign-off, P1-M10) |
| SEC-24 no clipboard writes except user copy | T-SEC-24: GUI test — conversion flow leaves clipboard untouched |

### 5.4 Gap closures added by this plan

- Security attack fixtures (XXE, zip bomb, traversal names, fuzz corpus) are added to
  the fixture set as family **S01–S08** (extends FIXTURE-PLAN.md).
- Golden matrix confirmed at ~45 cases (GOLDEN-CASE-REQUIREMENTS.md §5) plus GATE
  round-trip pairs.

## 6. Release checklist (P1-M10 gate)

Licence compliance (LGPL notices, Qt source link, THIRD-PARTY-NOTICES incl. ISO/SWIFT
attribution, Inno copyright) per docs/PACKAGING-STACK-RESEARCH.md checklist; signed
installer; VirusTotal scan; clean-VM offline install+convert test; SEC checklist rows
marked "release checklist" verified; docs make no lossless-round-trip claim.

## 7. Risks and mitigations (delta since Phase 0)

- mt-940 lacks a declared Python 3.14 classifier → CI matrix pins 3.12/3.13/3.14 from
  M0 (probes already passed on 3.14).
- BTC↔SWIFT code mapping is best-effort by design → shipped as a reviewable data file
  with `NMSC` fallback + loss note (never a hard failure).
- National restricted .02 subsets share the ISO namespace → we validate against the
  unrestricted ISO schema and surface subset violations as bank-data warnings, not
  product errors.
- openpyxl release stagnation → XlsxWriter (BSD-2) kept as drop-in export fallback.

## 8. Stop condition

This plan ends Phase 1 authorisation: implementation (P1-M0 onward) begins only on
separate owner approval. No `src/` exists yet.
