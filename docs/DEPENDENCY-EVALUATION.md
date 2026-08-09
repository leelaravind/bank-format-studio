# DEPENDENCY EVALUATION (Tasks 4, 5, 6)

Status: PHASE 0 RESEARCH. Research date: 2026-08-09. All facts verified against PyPI JSON metadata, PyPI project pages, and project repos. No packages installed for the product (research probes use a disposable venv only).

## Per-library dossier

| # | Library (PyPI) | Version (2026-08-09) | Licence (SPDX) | Transitive deps + licences | Maintenance evidence | Capabilities relevant to us | Risks | VERDICT |
|---|---|---|---|---|---|---|---|---|
| 1 | **mt-940** (import `mt940`) | 5.0.0 | BSD-3-Clause (confirmed via PyPI metadata + GitHub licence file) | **None** — zero runtime deps, pure stdlib, ships `py.typed` | Release 5.0.0 uploaded 2026-06-22; repo pushed 2026-08-01; 7 open issues; classifier "Development Status :: 6 - Mature" | Full MT940 parsing into typed collections; **opt-in tags + pre/post-processors for bank-specific variants** (e.g. `StatementGLS()`, `StatementASNB()`); fixtures cover ABN AMRO, ASN, GLS, jejik corpus and other EU banks | Python floor >=3.10; classifiers declare 3.10–3.13 — 3.14 not yet declared, but zero-dependency pure-Python makes breakage unlikely (verify in CI) | **APPROVED** |
| 2 | **mt940** (no hyphen, Tryton/B2CK) | 0.8.1 | BSD-3-Clause | None | Releases 2025-11-24 → 2026-04-03; maintained by Tryton Foundation | Basic MT940 parsing; py>=3.9 | Minimal feature set — no bank-variant processor system; 0.x API | **RESEARCH ONLY** (viable BSD fallback) |
| 3 | **pain001** | 0.0.59 (Jan 2026) | Apache-2.0 OR MIT (dual) | Heavy: click, defusedxml, jinja2, jsonschema, pyyaml, xmlschema, rich (all MIT/Apache/BSD/PSF — no copyleft) | Actively released; py 3.10–3.14 | **Confirmed: GENERATES pain.001 payment-initiation XML from CSV/SQLite/JSON/Parquet. Does NOT parse camt.053 at all.** | Wrong capability; 0.0.x versioning; large dep footprint | **REJECTED** (wrong capability; licence itself is fine) |
| 4 | **sepaxml** | 2.7.0 | MIT | xmlschema (MIT) + **text-unidecode 1.3 (Artistic/GPLv2+ dual, last release 2019)** | 2.7.0 released 2025-09-02; classifiers stale | **Confirmed scope: generates SEPA pain.001 / pain.008. No camt parsing.** | Wrong capability; text-unidecode copyleft flag if ever adopted | **REJECTED** (wrong capability) |
| 5a | **pycamt** | 1.1.1 | MIT | lxml>=6.0.2 (BSD-3-Clause) | 1.0.x 2024-03, 2-year gap, 1.1.x 2026-07-21; single author | Parses camt.053 (claims multiple versions) | Young, one maintainer, no XSD validation story, unclear version coverage | **RESEARCH ONLY** |
| 5b | **okane** | 0.4.0 (2026-05-20) | MIT | lxml (BSD), pydantic ~2.5 (MIT) | Alpha status | camt.053 → Pydantic models | **Targets the Czech Banking Association dialect** — not general camt.053 | **REJECTED** for product use (reading material only) |
| 6 | **lxml** | 6.1.1 (2026-05-18) | BSD-3-Clause; bundled libxml2/libxslt MIT | None required | Released 2026-05-18; **win_amd64 AND win_arm64 wheels confirmed for cp312, cp313, cp314** | Fast C parsing/serialization, XPath 1.0, **XSD 1.0 validation** (`etree.XMLSchema`), c14n, hardening knobs (`resolve_entities=False`, `no_network=True`, `huge_tree=False`) | Binary wheel per Python version; XSD 1.0 only (fine — camt schemas are XSD 1.0) | **APPROVED** |
| 7 | **xmlschema** | 4.3.2 (2026-06-30) | MIT | elementpath 5.1.4 (MIT, no deps) — the whole tree | Steady cadence 2025–2026 (sissaschool/Brunato); py 3.10–3.15 | Pure-Python **XSD 1.0 and 1.1** validation, XML↔dict decoding, **structured validation errors carrying XPath location + reason + schema particle** — directly usable for human-readable error translation | Slower than lxml on very large files (irrelevant for statements) | **APPROVED** |
| 8 | **defusedxml** | 0.7.1 (2021) | PSF-2.0 | None | Dormant since 2021 but stable/complete | Wrappers blocking entity expansion / DTD / external-entity attacks for stdlib parsers | Stale classifiers but works on 3.12+; partially superseded by stdlib hardening | **APPROVED** (defense-in-depth) |
| 9 | **openpyxl** | 3.1.5 (2024-06-28) | MIT | et-xmlfile 2.0.0 (MIT) | Slow cadence (26 months) but canonical and hugely deployed | Read AND write xlsx — covers Excel import+export | Release stagnation; CI-verify on 3.14. Alternative: **XlsxWriter (BSD-2-Clause, active)** — write-only, optional export backend | **APPROVED** (with CI pin + 3.14 smoke test) |
| 10 | stdlib **csv** | n/a | PSF-2.0 | n/a | n/a | Dialect control, quoting — fully sufficient | None | **APPROVED** |
| 11 | **jGnash MT940 code** | n/a | GPLv3 | n/a | n/a | n/a | GPL — forbidden in product | **REJECTED — do not read/copy code; academic reference only** |

Also surfaced: `bankstatementparser` (pandas dependency chain, breadth-over-depth) — unsuitable for a lean closed-source core; not evaluated further.

## camt.053 architecture decision (Task 5, point 6)

**Build camt.053 handling ourselves on lxml + own normalized model + own serializer + official XSD validation. Do not depend on any third-party camt library.**

- The third-party field is weak: `pycamt` = one maintainer, 2-year gap, no validation story; `okane` = alpha Czech-dialect parser; everything else is generation-side (pain.001/pain.008).
- None provides camt.053 **writing**, which MT940→camt requires — a serializer must be written regardless.
- camt.053 is a stable, well-schematized XSD 1.0 format; the hard part is the normalized model (needed anyway as the hub), not XML plumbing.
- Owning the code eliminates supply-chain/licence drift in a closed-source product and gives control over version coverage and error messages.
- `pycamt`/`okane` remain RESEARCH ONLY for field-mapping conventions (both MIT; do not copy code verbatim).

## Validation stack decision (Task 6)

**Primary validation library: `xmlschema` (MIT).** Pure Python (deterministic, zero ABI churn on 3.12–3.15), fully offline against bundled XSDs, XSD 1.0 and 1.1, and — decisive — **structured `XMLSchemaValidationError` objects with XPath paths, offending values and schema reasons**, mapping cleanly onto human-readable error translation.

- Schema resolution: camt XSDs are self-contained (no imports); schemas are bundled with the app and loaded from the local install directory only — never fetched. Any `schemaLocation` hints in input files are ignored.
- `lxml` stays as parse/serialize engine (speed, c14n, encoding handling, hardened parser flags); its `etree.XMLSchema` is a C-speed fallback validator.
- XXE posture on Python 3.12+: stdlib ElementTree never resolves external entities; bundled Expat >=2.4 has billion-laughs protection; lxml parsers constructed with `resolve_entities=False, no_network=True, dtd_validation=False, huge_tree=False`. DTDs in input files are rejected. `defusedxml` retained as defense-in-depth.

## Approved closed-source-safe core

`mt-940` + `lxml` + `xmlschema` (+`elementpath`) + `defusedxml` + `openpyxl` (+`et-xmlfile`) + stdlib `csv`.
No GPL/AGPL/LGPL anywhere in the approved runtime tree — all BSD-3-Clause/MIT/PSF. (GUI layer PySide6 is LGPL-dynamic — see PACKAGING-STACK-RESEARCH.md.)
The only copyleft flag found anywhere was text-unidecode (Artistic/GPL dual) under the rejected `sepaxml`.

## Licence-verification sources

- mt-940: https://pypi.org/project/mt-940/ · https://github.com/WoLpH/mt940/blob/develop/LICENSE
- mt940 (Tryton): https://pypi.org/project/mt940/
- pain001: https://pypi.org/project/pain001/ · https://github.com/sebastienrousseau/pain001/blob/main/LICENSE-MIT
- sepaxml: https://pypi.org/project/sepaxml/ · https://github.com/raphaelm/python-sepaxml/blob/master/LICENSE · https://pypi.org/project/text-unidecode/
- pycamt: https://pypi.org/project/pycamt/ · https://github.com/ODAncona/pycamt
- okane: https://pypi.org/project/okane/ · https://github.com/tkarabela/okane
- lxml: https://pypi.org/project/lxml/ · https://github.com/lxml/lxml/blob/master/LICENSES.txt
- xmlschema: https://pypi.org/project/xmlschema/ · https://github.com/sissaschool/xmlschema/blob/master/LICENSE
- elementpath: https://pypi.org/project/elementpath/ · https://github.com/sissaschool/elementpath/blob/master/LICENSE
- defusedxml: https://pypi.org/project/defusedxml/ · https://github.com/tiran/defusedxml/blob/main/LICENSE
- openpyxl: https://pypi.org/project/openpyxl/ · https://foss.heptapod.net/openpyxl/openpyxl/-/blob/branch/3.1/LICENCE.rst · https://pypi.org/project/et-xmlfile/
