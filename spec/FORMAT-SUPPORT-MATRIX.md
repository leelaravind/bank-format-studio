# FORMAT SUPPORT MATRIX

Status: PHASE 0 RESEARCH. Date: 2026-08-09. Final scope decision: see V1-SCOPE-RECOMMENDATION.md.

## V1 target matrix

| Format / version | Read (parse) | Write (generate) | Validate | Notes |
|---|---|---|---|---|
| MT940 (bare-tag files) | **V1** | **V1** | structural + reconciliation (no official XSD exists) | via approved `mt-940` library + variant profiles |
| MT940 ({1:}{2:}{4:} FIN envelope) | **V1** (tolerate/strip) | V1 optional (emit bare-tag by default) | structural | envelope round-trip fidelity not promised |
| MT940 bank variants (NL structured :86:, German GVC, :NS: tags) | **V1** (profiles: default, NL-structured, DE-GVC; tolerant fallback) | V1 writes ONE documented output convention | — | see FORMAT-NOTES.md §5 |
| camt.053.001.02 | **V1** | **V1** | official XSD (bundled) + reconciliation | SEPA-era installed base |
| camt.053.001.08 | **V1** | **V1** | official XSD (bundled) + reconciliation | CBPR+ / post-Nov-2025 European mandate |
| camt.053.001.14 | detect + report only | no | schema collected (reference) | do not promise runtime support in V1 |
| camt.053 other versions (.03–.07, .09–.13) | detect + clear "unsupported version" error | no | no | namespace detection required |
| CSV (documented dialect, CSV-FORMAT-STRATEGY.md) | **V1** | **V1** | column/type validation + reconciliation | the product's own interchange dialect only |
| Arbitrary foreign bank CSVs | **NOT V1** | — | — | unbounded scope; future column-mapping feature |
| Excel .xlsx | **V1 export**; import stretch goal | **V1** (render of CSV tables via openpyxl) | as CSV rules | keep import out of V1 commitments |
| camt.052 / camt.054 | no | no | no | future scope; architecture must not preclude |
| BAI2 | no | no | no | future scope (see below) |
| MT942 | no | no | no | future scope; MT940 parser groundwork reusable |
| PDF statements / OCR / bank APIs | no | no | no | explicitly out of scope |

## Conversion directions (V1)

| From \ To | MT940 | camt.053 (.02/.08) | CSV | XLSX |
|---|---|---|---|---|
| MT940 | — | **V1** | **V1** | **V1** |
| camt.053 .02/.08 | **V1** (with documented loss report) | version up/down-convert: **V1** (.02↔.08) | **V1** | **V1** |
| CSV (own dialect) | **V1** (reconstruction from core fields) | **V1** (reconstruction) | — | **V1** |
| XLSX | not V1 | not V1 | not V1 | — |

Every conversion emits: reconciliation result (INV-1..8) + information-loss report.

## BAI2 future-scope note (Task 17 evidence)

BAI2 was NOT collected in Phase 0. Adding it later requires: BAI2 specification access
(published by BAFJ/AFP — the current "BAI2" spec is distributed by AFP; licence/redistribution
terms unverified), US-style fixture set, and type-code mapping tables. Risk is moderate,
not low — keep out of V1 and re-run a Phase-0-style collection for it before committing.
