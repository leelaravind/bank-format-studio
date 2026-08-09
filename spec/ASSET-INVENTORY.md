# ASSET INVENTORY

Status: PHASE 0. Date: 2026-08-09. Full provenance (URLs, SHA256, licences): docs/SOURCE-PROVENANCE.md.

## In-repository assets

| Category | Location | Count | State |
|---|---|---|---|
| camt.053 official XSDs (.001.02, .001.08, .001.14) | `references/camt053/` | 3 | verified well-formed, correct namespaces, probe-validated |
| SWIFTStandards IPR EULA copy | `references/camt053/licensing/` | 1 | stored (internal reference) |
| camt.053 samples (official ISO example + genkgo MIT fixtures) | `sample-data/public/camt053/` | 7 + licence file | all XSD-validate (Probe 3: 0 failures) |
| MT940 variant fixtures (WoLpH/mt940 corpus: NL, DE, PL, HU) | `sample-data/public/mt940/` | 9 | all parse (Probe 1/2; ASNB needs variant handler) |
| Fixture licence texts (BSD-3-Clause, MIT ×2, Apache-2.0) | `references/licences/` | 4 | retained per licence terms |
| Research probes + results | `research-probes/` | 3 scripts + PROBE-RESULTS.md | disposable, not product code |
| Requirements / research documents | `spec/`, `docs/` | 13 | this source pack |

## Evaluated but not vendored (Phase 0 policy: nothing vendored)

Python packages (verified on PyPI, installed only in a disposable probe venv):
mt-940 5.0.0, lxml 6.1.1, xmlschema 4.3.2, elementpath 5.1.4, defusedxml 0.7.1,
openpyxl 3.1.5, et-xmlfile 2.0.0. GUI/packaging candidates (not installed):
PySide6 6.11.1, PyInstaller, Inno Setup.

## Known gaps (deliberate)

- No synthetic fixtures yet (plan exists: spec/FIXTURE-PLAN.md; generation is a later phase).
- No golden cases yet (structure defined: spec/GOLDEN-CASE-REQUIREMENTS.md).
- No BAI2 assets (out of V1 scope by decision).
- camt.053.001.14 stored for reference only — not a V1 runtime target.
- iso20022.org direct-download re-verification pending (owner action; Wayback captures hash-recorded).

## Directory map

```
references/
  camt053/            camt.053.001.02/.08/.14.xsd + licensing/SWIFTStandards_LIC_OUT_V5.pdf
  iso20022/           (reserved — general ISO 20022 references)
  mt940/              (reserved — no redistributable MT940 spec exists; see docs/FORMAT-NOTES.md)
  licences/           fixture licence texts
sample-data/
  public/mt940/       9 bank-variant fixtures
  public/camt053/     7 validated samples + MIT licence
  synthetic/          (empty — future phase)
tests/
  fixtures/           (empty — future phase)
  golden-cases/       (empty — future phase)
```
