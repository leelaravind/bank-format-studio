# SYNTHETIC FIXTURE PLAN

Status: PHASE 0 RESEARCH — plan only. Fixtures themselves are generated in a later phase
(except minimal proof fixtures used to validate the source pack).
Date: 2026-08-09

Rules: no real customer data, ever. Every synthetic file carries a header comment/marker
(where format allows) and a `SYNTHETIC` label in its provenance entry. Public fixtures
(from permissively-licensed repos) live in `sample-data/public/`; synthetic ones in
`sample-data/synthetic/`; test-ready copies are organized under `tests/fixtures/`.

Synthetic data conventions: fictional IBANs built from valid check digits with test
bank codes, BIC pattern `XXXXDEXX`/`TESTGB2L`-style test BICs, party names drawn from
obviously fictional set ("Acme Tooling GmbH", "Jane Example"), amounts chosen so every
statement satisfies INV-1 exactly unless the fixture is deliberately inconsistent.

## MT940 fixtures

| ID | Fixture | Purpose | Validity |
|---|---|---|---|
| M01 | valid basic statement, 2 tx, credit+debit, bare `:20:`-first format | happy path | VALID |
| M02 | multi-transaction (≥10 tx), mixed C/D, `:86:` unstructured | volume/happy path | VALID |
| M03 | debit-only statement | sign handling | VALID |
| M04 | credit-only statement | sign handling | VALID |
| M05 | zero-transaction statement (`:60F:`→`:62F:`) | E1 | VALID |
| M06 | malformed tag (`:6X:`, or `:61:` bad date) | parser error path | INVALID |
| M07 | invalid currency code (`EU0`) | validation error | INVALID |
| M08 | missing `:60F:` | hard error | INVALID |
| M09 | missing `:62F:` (truncated file) | E11 hard error | INVALID |
| M10 | duplicate transaction lines | E7 warning | VALID+WARN |
| M11 | balance mismatch (declared `:62F:` ≠ computed) | E10 reconciliation failure | VALID-SYNTAX / FAIL-RECON |
| M12 | multi-page `:60M:/:62M:` chain, 2 pages | E2/INV-4 | VALID |
| M13 | reversal marks RD and RC | E3 | VALID |
| M14 | German GVC structured `:86:` (`?20?21...` subfields) | bank-variant parsing | VALID |
| M15 | Dutch-style structured `:86:` (`/EREF/.../REMI/`-convention) | bank-variant parsing | VALID |
| M16 | with `{1:}{2:}{4:}` SWIFT block envelope | envelope handling | VALID |
| M17 | `:64:` + repeated `:65:` present | balance-type breadth | VALID |
| M18 | unknown non-standard tag (`:NS:`) | unknown-field tolerance + warning | VALID+WARN |
| M19 | 15-digit amount, JPY (0-decimal) currency | E9/E14 | VALID+WARN |
| M20 | year-boundary entry date (value date 2026-01-02, entry MMDD 1230) | booking-date year heuristic | VALID |

## camt.053 fixtures (per supported schema version)

| ID | Fixture | Purpose | Validity |
|---|---|---|---|
| C01 | valid basic statement, 2 entries | happy path | VALID |
| C02 | multiple transactions, debits+credits, TxsSummry present | INV-5 | VALID |
| C03 | remittance: Ustrd multi-line + Strd creditor reference | mapping breadth | VALID |
| C04 | multiple balance types (OPBD, CLBD, CLAV, FWAV, PRCD) | E5 | VALID |
| C05 | schema-invalid (wrong element order / missing required CdtDbtInd) | XSD error path | INVALID (XSD) |
| C06 | balance mismatch (CLBD ≠ OPBD + movements) | E10 | VALID-XSD / FAIL-RECON |
| C07 | reversal entry (RvslInd=true) | E3 | VALID |
| C08 | batch entry (1 Ntry, 3 TxDtls) | E13 | VALID |
| C09 | entry with Sts=PDNG | E6 warning/exclusion | VALID-XSD +WARN |
| C10 | unknown/unsupported optional element present (e.g. Intrst) | tolerance + loss note | VALID |
| C11 | non-account currency entry (AmtDtls with exchange) | INV-3 | VALID+WARN |
| C12 | zero-entry statement | E1 | VALID |
| C13 | wrong namespace/version mismatch (file claims .02, content .08 shape) | version detection error | INVALID |
| C14 | empty-but-schema-valid edge (minimal mandatory elements only) | minimality | VALID |

## CSV fixtures

| ID | Fixture | Purpose |
|---|---|---|
| V01 | canonical transactions.csv + statements.csv pair exported from M01 equivalent | round-trip base |
| V02 | CSV with formula-injection payloads (`=cmd`, `+1+1`, `@SUM`) | security handling |
| V03 | CSV with quoted fields, embedded commas/newlines, UTF-8 BOM | parser robustness |
| V04 | CSV missing required column | validation error |
| V05 | CSV with bad date/amount formats | validation error |
| V06 | CSV round-trip: CSV→MT940→CSV and CSV→camt→CSV comparison set | reconstruction limits |

## Security fixtures (S-family, required by IMPLEMENTATION-PLAN.md §5.4)

All SYNTHETIC, adversarial by design; live in `tests/fixtures/security/`. Expected
behaviour is always a controlled, human-readable error or neutralization — never a
crash, hang, network access, or file write outside the chosen output directory.

| ID | Fixture | Attack class | Expected behaviour | SEC refs |
|---|---|---|---|---|
| S01 | camt-like XML with internal DTD + external entity (`<!ENTITY xxe SYSTEM "file:...">`) and an entity referencing an external URL | XXE / external entity | rejected before schema validation: `E_XML_DTD_FORBIDDEN`; no file read, no network | SEC-13 |
| S02 | "billion laughs" nested-entity expansion XML | entity-expansion DoS | rejected: `E_XML_DTD_FORBIDDEN` / expansion limit; bounded memory/time | SEC-13, SEC-14 |
| S03 | valid-looking camt.053 whose `xsi:schemaLocation` points to an external URL, plus a variant with a remote namespace | malicious schema-location | hint ignored; validated ONLY against bundled local XSD; zero network resolution | SEC-02, SEC-13 |
| S04 | statement whose statement-id/account fields contain `..\..\evil`, `CON`, `PRN`, `NUL.txt`, trailing dots/spaces, control characters (drives output-filename derivation) | path traversal / reserved names | sanitized output name; final resolved path verified inside chosen directory; `W_FILENAME_SANITIZED` | SEC-08 |
| S05 | crafted XLSX: (a) zip bomb (high compression ratio, huge uncompressed size), (b) archive member named `..\..\member.xml` | zip bomb / archive traversal | rejected before extraction: `E_XLSX_UNSAFE_ARCHIVE`; bounded memory | SEC-15 |
| S06 | CSV with formula payloads (`=cmd`, `+1+1`, `-2+3`, `@SUM(A1)`, tab/CR-prefixed) in text fields (extends V02) | spreadsheet formula injection | import: inert strings (SEC-17); export in Excel-safe mode: apostrophe-neutralized, numeric amount cells exempt (SEC-16) | SEC-16, SEC-17 |
| S07 | malformed/resource-exhaustion set: MT940 with a multi-MB single `:86:`, XML with pathological attribute counts, oversized file over the documented cap, truncated-mid-tag inputs | resource exhaustion | size/line/repetition caps enforced with `E_INPUT_TOO_LARGE`-class errors; parse time bounded | SEC-14 |
| S08 | fuzz-lite corpus: deterministic mutations (bit flips, truncations, tag shuffles) of M06/C05 seeds, generated by a seeded script at test time | robustness fuzzing | never crashes/hangs; every outcome is a typed error/warning; corpus generation is deterministic (fixed seed) | SEC-14 |

## Cross-format golden conversion set

Every VALID MT940 fixture (M01–M05, M12–M20) gets a corresponding expected camt.053
and CSV output; C01–C04, C07, C08, C12 get expected MT940 and CSV outputs — these form
the golden cases (see GOLDEN-CASE-REQUIREMENTS.md). Deliberately-invalid fixtures get
expected error/warning transcripts instead.

## Generation approach (later phase)

Hand-authored from verified format rules (not generated by unverified libraries), then
cross-checked: camt files must pass official XSD validation; MT940 files must parse in
the approved third-party parser AND satisfy INV-1 by construction; disagreements
investigated before a fixture is accepted as golden.
