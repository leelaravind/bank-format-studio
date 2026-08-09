# SOURCE PACK — Bank Statement Format Studio

Phase 0 deliverable. Compiled 2026-08-09. This document is the summary and verdict;
the supporting evidence lives in the documents it references.

## Document map

| Document | Content |
|---|---|
| spec/ASSET-INVENTORY.md | What was collected, where it lives, known gaps |
| spec/FORMAT-SUPPORT-MATRIX.md | Format × read/write/validate matrix for V1 and future |
| spec/DATA-MAPPING-RESEARCH.md | Normalized model, field-by-field mapping, round-trip loss analysis |
| spec/RECONCILIATION-REQUIREMENTS.md | Balance invariants INV-1..8, edge cases E1..E14 |
| spec/CSV-FORMAT-STRATEGY.md | V1 CSV interchange dialect proposal |
| spec/FIXTURE-PLAN.md | Synthetic fixture set design (M01–M20, C01–C14, V01–V06) |
| spec/GOLDEN-CASE-REQUIREMENTS.md | Golden-case structure, manifest schema, rules |
| spec/V1-SCOPE-RECOMMENDATION.md | Scope decision (Option C with guardrails) |
| docs/SOURCE-PROVENANCE.md | Register of every external asset: URL, publisher, licence, SHA256 |
| docs/LICENCE-AUDIT.md | GREEN/AMBER/RED classification of every dependency/asset |
| docs/DEPENDENCY-EVALUATION.md | Per-library dossiers and verdicts (Tasks 4–6) |
| docs/FORMAT-NOTES.md | Original MT940 technical summary + bank-variation matrix |
| docs/PACKAGING-STACK-RESEARCH.md | Desktop stack comparison and single recommendation |
| docs/SECURITY-REQUIREMENTS.md | SEC-01..24 binding security/privacy requirements |
| research-probes/PROBE-RESULTS.md | Verification probe outcomes |

---

# SOURCE PACK VERDICT

STATUS:

**READY FOR IMPLEMENTATION PLANNING**

All required assets for the recommended V1 scope are collected, licence-cleared, and
probe-verified. No blocking gaps. Two follow-ups are owner conveniences, not blockers
(see Required Owner-Provided Assets).

## Assets Successfully Collected

- **camt.053 XSDs**: official camt.053.001.02 and .001.08 (V1 targets) + .001.14 (reference), byte-exact captures of official iso20022.org URLs, self-contained, namespace-verified, loadable in both candidate validators; SHA256s recorded. SWIFTStandards IPR EULA copy stored.
- **camt.053 samples (7)**: official ISO example instance + 6 MIT-licensed genkgo fixtures covering minimal statement, multi-statement, all balance types, 5-decimal amounts, parties/remittance, batch entry with FX, and v8. **All validate against the bundled XSDs (0 failures).**
- **MT940 fixtures (9 variants)**: ASNB (FIN blocks), ABN AMRO, ING, Rabobank (structured `:86:`), German SEPA/GVC, German legacy (DEM), German GVC code words, mBank (PL), Sberbank Hungary (`:NS:` tags) — BSD-3-Clause/MIT/Apache-2.0, licence texts retained. **All parse with the approved library** (ASNB via its bank-variant mechanism). Exceeds the required three meaningfully different variants.
- **MT940 technical summary**: original compilation (docs/FORMAT-NOTES.md) from legally accessible public references, with bank-variation matrix and bibliography; no proprietary SWIFT documentation copied.
- **Library verdicts**: approved closed-source-safe core (mt-940, lxml, xmlschema, elementpath, defusedxml, openpyxl, et-xmlfile, stdlib csv) — all verified current, maintained, and permissively licensed; all install and run on Python 3.14/Windows 11.
- **Packaging direction**: fully licence-verified recommendation (PySide6 LGPL-dynamic + PyInstaller with bootloader exception + Inno Setup + code signing).

## Assets Verified but Not Redistributable

- Rabobank MT940S format PDF (copyright-restricted — facts used, never bundle/quote).
- Bank format guides: kontopruef.de, HypoVereinsbank, National-Bank, Goldman Sachs, ABN AMRO, Danske Bank (URL recorded but fetch failed — unverified).
- Goldman Sachs / Bank of America camt.053 samples; SWIFT MyStandards CBPR+ instances (login-only); Deutsche Bank / DZ Bank migration guides.

## Synthetic Assets Required

- All golden reconciliation cases must be synthetic: probes proved most public MT940 fixtures are **parse-quality only** (balances deliberately don't reconcile; one lacks a closing balance). Plan: spec/FIXTURE-PLAN.md (M01–M20, C01–C14, V01–V06) + security attack fixtures (XXE, zip-bomb, path traversal, formula injection).
- camt.053.001.08-rich samples are thin publicly (1 collected) — synthesize v8 fixtures from the official XSD.

## Missing Assets

None blocking. Non-blocking:
- Direct iso20022.org re-download to confirm Wayback capture hashes (owner action, trivial).
- Danske Bank extended MT940 guide unverified (redundant — two agreeing sources cover the same ground).
- BAI2 spec/fixtures — deliberately not collected (out of V1 scope).

## Licensing Risks

- **Zero RED items** in the proposed build (docs/LICENCE-AUDIT.md).
- AMBER with satisfiable conditions: PySide6/Qt (LGPL-3.0 dynamic: notices, replaceable DLLs, Qt source link), PyInstaller (bootloader exception), ISO 20022 XSDs (attribution; may not sell schemas as such).
- Residual: SWIFTStandards EULA is from 2005 (referenced as current by the ISO 20022 RA); text-unidecode copyleft exists only under the **rejected** sepaxml; jGnash (GPLv3) referenced academically only, no code read or copied.

## Format Ambiguities

- `:61:` subfield 9 (supplementary details) semantics differ per bank — treat as opaque by default.
- MT940 entry date has no year — boundary heuristic required; impossible dates (Feb 30) occur in the wild.
- `:86:` has three structural families (unstructured, slash code words, German GVC `?nn`) — variant profiles required; code words split mid-word across subfield boundaries.
- Amount tolerance required: bare trailing comma, missing comma, zero-padding, >2 decimals.
- Encodings: SWIFT X charset is a floor — real files carry CP1250/CP1252 bytes, tabs, soft hyphens.
- National *restricted* camt.053.001.02 schemas share the ISO namespace — files may follow a subset; parse against the unrestricted ISO schema.
- MT940 ↔ camt.053 is **not lossless** (spec/DATA-MAPPING-RESEARCH.md): structured parties/remittance, batch entries, BTC domain codes, >16-char references degrade toward MT940; funds code/supplementary layout degrade toward camt. Information-loss reporting is a V1 requirement.

## Bank-Specific Compatibility Risks

- Nine collected variants already span: FIN-block vs bare-tag envelopes, proprietary preambles (`:940:`, ABN 3-line, ING header), `:28:` vs `:28C:`, non-standard `:NS:` tags, space-padded type codes, funds-code oddities, missing entry dates, missing closing balances.
- The mt-940 test corpus maps further variants not yet collected (citi, Knab, SNS, Triodos, PostFinance, Raiffeisen) — available under the same BSD licence if needed.
- Strategy: tolerant reader with variant profiles; ONE documented output convention; never promise emulation of specific banks' output.

## Recommended V1 Format Scope

**Option C with guardrails** (spec/V1-SCOPE-RECOMMENDATION.md): MT940 ↔ camt.053.001.02+.08 ↔ own-dialect CSV, plus XLSX export. CSV import limited to our documented dialect; XLSX import a stretch goal; BAI2/camt.052/camt.054/MT942 future scope. Key driver: the Nov 2025 European MT940→camt.053.001.08 migration makes bidirectional conversion the commercial core.

## Recommended Technical Stack

- Core: **Python 3.12+**, `mt-940` (BSD-3-Clause) for MT940 parsing + own variant layer; **self-built camt.053 reader/writer** on `lxml`; **`xmlschema`** as primary XSD validator (structured, human-translatable errors); `defusedxml` defense-in-depth; `decimal`-exact arithmetic; stdlib `csv`; `openpyxl` for XLSX.
- GUI/packaging: **PySide6 (Qt Widgets, LGPL-dynamic) → PyInstaller `--onedir` → Inno Setup → code-signed** (Microsoft Trusted Signing preferred). Compliance checklist in docs/PACKAGING-STACK-RESEARCH.md.
- Security posture: SEC-01..24 (fully offline, hardened XML parsing, path sanitization, formula-injection guard, no telemetry).

## Required Owner-Provided Assets

Only items Claude Code cannot legitimately obtain:

1. **Code-signing identity** (blocking for release, not for implementation): apply for Microsoft Trusted Signing (~$9.99/mo; eligibility depends on your legal entity/country) or purchase an OV cloud-HSM certificate (~$250–550/yr). Requires your legal identity documents. Decide the legal entity name shown on SmartScreen prompts first.
2. **iso20022.org browser re-download** (5 minutes): fetch camt.053.001.02/.08/.14 from iso20022.org in a normal browser (the site blocks automated clients) and confirm the SHA256s in docs/SOURCE-PROVENANCE.md §B.1. Until then the Wayback-capture provenance stands, namespace-verified.
3. **Optional, only if you want real-world conformance testing beyond public fixtures**: one or two real MT940/camt.053 exports from *your own* bank account(s), sanitized, used strictly as internal dev material — never redistributed. Not required for planning.
4. **Merchant-of-record account** (Lemon Squeezy or Gumroad) — future phase, listed for completeness.

Nothing else: schemas, samples, licences, and library verification are complete in-repo.

---

## STOP

Phase 0 ends here per instructions. No implementation plan has been written; no product
code exists. The next phase (implementation planning) awaits separate owner authorisation.
