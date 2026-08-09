# V1 FORMAT SCOPE RECOMMENDATION (Task 17)

Status: PHASE 0 conclusion. Date: 2026-08-09.

## Options considered

- **OPTION A:** MT940 → camt.053 + CSV (one-way)
- **OPTION B:** MT940 ↔ camt.053 + CSV (bidirectional core, CSV export)
- **OPTION C:** MT940 ↔ camt.053 ↔ CSV/Excel (full triangle incl. CSV import)

## Recommendation: OPTION C, with two precise guardrails

**V1 = MT940 ↔ camt.053 (.001.02 and .001.08) ↔ CSV (own documented dialect), plus
XLSX export.** Guardrails: (1) CSV *import* is restricted to the product's own
documented dialect — no "bring any bank CSV" promise; (2) XLSX *import* is a stretch
goal, not a commitment.

### Why not A (one-way)

The commercial driver discovered in research is the **November 2025 European
migration** (German DK and others retired MT940 in favour of camt.053.001.08): the
highest-value customer job is *both* directions — legacy systems that still need
MT940 fed from camt-only banks (camt→MT940), and archives/tools that need camt or
spreadsheets from old MT940 files (MT940→camt/CSV). One-way conversion halves the
addressable use cases for nearly the same engineering cost, because the normalized
model, both parsers, reconciliation and validation are needed regardless; only the
serializers differ, and the MT940 serializer is the smaller of the two.

### Why not stop at B (no CSV import)

CSV→MT940/camt is the accountant workflow (fix or assemble statements in Excel,
re-emit a bank format). Because the CSV dialect is **our own, fully specified**
format (CSV-FORMAT-STRATEGY.md), importing it is cheap and testable — it's parsing
our own output. The expensive, risky thing would be importing *arbitrary* bank CSVs;
that is explicitly excluded.

### Why the two-version camt target (.02 + .08)

Evidence (see SOURCE-PROVENANCE.md, PACKAGING/ISO agent findings):
- **.001.02** — the SEPA-era workhorse; a decade of installed base; many banks still emit it; most historical files a desktop converter encounters are .02.
- **.001.08** — CBPR+/SWIFT MX standard for cash-management reporting and the version the German DK migrated to in Nov 2025; Swiss Payment Standards likewise.
- Versions .03–.07 and .09–.14 have no major statement-scheme mandate; **.001.14** (current latest) is collected for reference so V1 element decisions can be future-checked, but is not a runtime target.
- Both XSDs are collected, licence-cleared for bundling, self-contained, and probe-verified (Probe 3, 0 failures).

### Honesty constraints attached to the recommendation

- Never claim lossless round-trip: DATA-MAPPING-RESEARCH.md documents structural loss camt→MT940 (structured parties/remittance, batch entries, BTC codes, >16-char references) and MT940→camt (funds code, supplementary-details layout). Every conversion ships an information-loss report.
- camt→MT940 output uses ONE documented `:86:` convention; bank-variant *input* tolerance is broad, output emulation of specific banks is not promised.
- Reconciliation (INV-1..8) is a release gate for every conversion.

### BAI2

Remains **future scope**. Collection proved nothing about BAI2 being low-risk: the
spec is distributed by AFP with unverified licensing, no fixture set was collected,
and its type-code system needs its own mapping research. Re-run a Phase-0-style
collection for BAI2 before ever committing to it.

### Smallest commercially credible scope, restated

MT940 (read tolerant / write one convention) ↔ camt.053.001.02+.08 (read/write,
XSD-validated) ↔ own-dialect CSV (read/write) + XLSX export; balance reconciliation
and loss reporting on every conversion; everything local/offline.
