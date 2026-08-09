# bank-format-studio

**Bank Statement Format Studio** — a local/offline desktop utility that converts and
validates structured bank statement formats: MT940 ↔ ISO 20022 camt.053 ↔ CSV/Excel,
with deterministic conversion, XSD validation, balance reconciliation and
human-readable errors. No bank data ever leaves the machine.

## Repository status: PHASE 0 — SOURCE PACK

This repository currently contains **research and requirements only**. No product
code exists yet. See `spec/SOURCE-PACK.md` for the source-pack verdict and
`docs/SOURCE-PROVENANCE.md` for the provenance of every external asset.

```
spec/             requirements & research (mapping, reconciliation, CSV, fixtures, golden cases, scope)
references/       collected schemas & licence texts (see provenance register)
sample-data/      public fixtures (with provenance) and synthetic samples
tests/            reserved for future fixtures/golden cases
docs/             provenance register, licence audit, security requirements, format notes
research-probes/  disposable verification scripts (not product code)
```
