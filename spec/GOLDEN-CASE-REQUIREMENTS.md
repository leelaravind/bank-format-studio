# GOLDEN TEST CASE REQUIREMENTS

Status: PHASE 0 — structure definition only. Golden cases are authored in a later phase.
Date: 2026-08-09

## 1. Purpose

Golden cases are the product's ground truth: input file → expected normalized model →
expected output file(s) → expected reconciliation figures → expected diagnostics.
They encode only **verified format semantics** (from the collected source pack);
no financial rules may be invented. Any golden value that cannot be justified by a
cited specification rule or by arithmetic is not admissible.

## 2. Directory layout (future `tests/golden-cases/`)

```
tests/golden-cases/<case-id>/
  case.yaml                # manifest (see §3)
  input/<file>             # exactly one input artefact (mt940|camt053|csv)
  expected/normalized.json # canonical JSON dump of the normalized model
  expected/<outputs>       # e.g. output.camt.053.001.02.xml, output.csv, output.sta
  expected/diagnostics.json# errors, warnings, information-loss notes
```

## 3. Manifest schema (`case.yaml`)

```yaml
id: G-M01-CAMT02            # unique, stable
title: basic MT940 to camt.053.001.02
input:
  file: input/basic.sta
  format: mt940             # mt940 | camt.053.001.02 | camt.053.001.08 | csv
  provenance: SYNTHETIC     # SYNTHETIC | PUBLIC(<asset-id from SOURCE-PROVENANCE>)
conversions:
  - target: camt.053.001.02
    expected_output: expected/output.camt.053.001.02.xml
  - target: csv
    expected_output: expected/output.csv
expected_model: expected/normalized.json
reconciliation:              # exact decimal strings, never floats
  opening_balance: "1250.00"
  opening_balance_dc: C
  total_credits: "3100.50"
  total_debits: "890.25"
  credit_count: 3
  debit_count: 2
  closing_balance: "3460.25"
  closing_balance_dc: C
  currency: EUR
validation:
  expected_result: PASS      # PASS | FAIL_PARSE | FAIL_SCHEMA | FAIL_RECONCILIATION
  expected_errors: []        # stable error codes + human-message substrings
  expected_warnings:         # e.g. [W_DUPLICATE_ENTRY, W_JPY_DECIMALS]
information_loss:            # REQUIRED, may be empty list, never omitted
  - field: remittance line breaks
    direction: mt940->camt
    behaviour: collapsed to single Ustrd lines
notes: free text, cites the spec rule justifying any non-obvious expectation
```

## 4. Rules

1. **Determinism**: expected outputs are byte-exact (fixed ordering, fixed
   formatting, no timestamps — `CreDtTm` in generated camt files comes from a
   pinned test clock).
2. **Arithmetic**: reconciliation figures in every VALID case must satisfy
   INV-1 (RECONCILIATION-REQUIREMENTS.md) by construction; a case whose figures
   don't reconcile must declare `FAIL_RECONCILIATION`.
3. **Round-trip pairs**: for each A→B golden case with a documented-lossless core,
   a B→A′ companion case asserts INV-7/INV-8 conservation and lists exactly the
   expected field-level differences (must match DATA-MAPPING-RESEARCH.md).
4. **Diagnostics are golden too**: warnings and information-loss notes are
   asserted, not just tolerated — silent loss is a test failure.
5. **Provenance**: every input derived from a public fixture references its
   SOURCE-PROVENANCE asset ID; synthetic inputs are labelled SYNTHETIC.
6. **Error codes are stable API**: expected_errors reference symbolic codes, so
   later message-wording improvements don't break goldens.
7. **Schema validation**: every expected camt output must itself pass official
   XSD validation as part of the golden-case check (self-consistency gate).

## 5. Initial golden-case matrix (to build in a later phase)

From FIXTURE-PLAN.md: every VALID MT940 fixture × {camt.053.001.02, csv} targets;
every VALID camt fixture × {mt940, csv}; CSV round-trip set V06; plus one
FAIL_SCHEMA, one FAIL_PARSE, one FAIL_RECONCILIATION case per input format.
Estimated initial set: ~45 cases.
