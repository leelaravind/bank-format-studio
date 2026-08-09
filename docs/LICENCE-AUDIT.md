# LICENCE / COMMERCIAL AUDIT (Task 13)

Status: PHASE 0. Audit date: 2026-08-09. Verification URLs in DEPENDENCY-EVALUATION.md,
PACKAGING-STACK-RESEARCH.md and SOURCE-PROVENANCE.md.

Classification: **GREEN** safe · **AMBER** usable with conditions · **RED** do not use.
Rule: ZERO RED items may enter the build.

## 1. Runtime libraries (product core)

| Name | Ver | Licence | Commercial | Closed-source | Redistribution | Attribution | Source offer | Linking constraint | Patent concern | Class | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mt-940 | 5.0.0 | BSD-3-Clause | Yes | Yes | Yes | Retain licence text | No | None | None | GREEN | APPROVED |
| lxml (+bundled libxml2/libxslt) | 6.1.1 | BSD-3-Clause / MIT | Yes | Yes | Yes | Retain notices | No | None | None | GREEN | APPROVED |
| xmlschema | 4.3.2 | MIT | Yes | Yes | Yes | Retain licence text | No | None | None | GREEN | APPROVED |
| elementpath | 5.1.4 | MIT | Yes | Yes | Yes | Retain licence text | No | None | None | GREEN | APPROVED |
| defusedxml | 0.7.1 | PSF-2.0 | Yes | Yes | Yes | Retain notice | No | None | None | GREEN | APPROVED |
| openpyxl | 3.1.5 | MIT | Yes | Yes | Yes | Retain licence text | No | None | None | GREEN | APPROVED |
| et-xmlfile | 2.0.0 | MIT | Yes | Yes | Yes | Retain licence text | No | None | None | GREEN | APPROVED |
| Python stdlib (csv, decimal, ElementTree) | 3.12+ | PSF-2.0 | Yes | Yes | Yes | Retain PSF notice | No | None | None | GREEN | APPROVED |
| XlsxWriter (optional export backend) | current | BSD-2-Clause | Yes | Yes | Yes | Retain licence text | No | None | None | GREEN | OPTIONAL |

## 2. GUI / packaging layer (evaluated, not yet built)

| Name | Ver | Licence | Commercial | Closed-source | Conditions | Class | Decision |
|---|---|---|---|---|---|---|---|
| PySide6 / shiboken6 + Qt 6 | 6.11.1 | LGPL-3.0 (chosen from tri-licence) | Yes | Yes | Dynamic linking only (satisfied by construction); ship LGPL+GPLv3 texts; prominent notice; user-replaceable Qt DLLs (`--onedir`); link to exact Qt source version | **AMBER** | APPROVED WITH CONDITIONS (compliance checklist in PACKAGING-STACK-RESEARCH.md) |
| PyInstaller | current | GPL-2.0+ **with Bootloader Exception** | Yes | Yes | Exception explicitly permits closed-source bundling; do not distribute modified bootloader without source | **AMBER** | APPROVED WITH CONDITIONS (build tool, not shipped as library) |
| Inno Setup | current | Custom permissive (Inno Setup License) | Yes | Yes | Keep copyright notice, don't misrepresent origin | GREEN | APPROVED |
| Tkinter/Tcl-Tk (fallback GUI) | stdlib | PSF + Tcl BSD-style | Yes | Yes | Retain notices | GREEN | FALLBACK ONLY |
| NSIS (alt installer) | current | zlib | Yes | Yes | — | GREEN | ALTERNATE |
| Flet | 0.86.5 | Apache-2.0 | Yes | Yes | Pre-1.0 churn | GREEN (licence) | REJECTED (maturity, not licence) |
| Tauri v2 | current | MIT/Apache-2.0 | Yes | Yes | — | GREEN (licence) | REJECTED (architecture fit) |

## 3. Schemas

| Name | Ver | Licence / usage basis | Redistribution | Class | Decision |
|---|---|---|---|---|---|
| ISO 20022 camt.053 XSDs (.001.02, .001.08; .14 reference-only) | 2009–2026 | ISO 20022 IPR policy + SWIFTStandards IPR EULA (Sept 2005): world-wide, royalty-free, non-exclusive licence to develop software/products; sub-licensing royalty-free | Bundling unmodified XSDs in the product permitted; the schemas may NOT be sold as the product themselves; attribution "ISO 20022 message schemas © SWIFT/ISO 20022 Registration Authority, used under the SWIFTStandards IPR Policy EULA" in THIRD-PARTY-NOTICES; do not strip generator comments | AMBER | APPROVED WITH CONDITIONS (EULA copy at references/camt053/licensing/) |

## 4. Sample data / fixtures

| Asset | Licence | Redistribution | Attribution | Class | Decision |
|---|---|---|---|---|---|
| WoLpH/mt940 fixtures (asnb, gv_codes, mbank, sberbank) | BSD-3-Clause | Yes | Licence text retained (`references/licences/mt940-python-BSD-3-Clause.txt`) | GREEN | APPROVED (dev/test use; ship only if needed with notice) |
| jejik fixtures (abnamro, ing, rabobank) — Frank Oxener / Agile Dovadi BV | MIT | Yes | Licence text retained; attribute Frank Oxener | GREEN | APPROVED |
| betterplace fixture (sepa_snippet) | Apache-2.0 | Yes | Licence text retained; NOTICE obligations if shipped | GREEN | APPROVED |
| cmxl fixture (german) — Michael Bumann | MIT | Yes | Licence text retained | GREEN | APPROVED |
| ISO 20022 official camt.053.001.02 example instance | ISO 20022 IPR (royalty-free) | Yes | Notice in THIRD-PARTY-NOTICES | GREEN | APPROVED |
| genkgo/camt fixtures (6 files, v2 + v8) | MIT | Yes | Licence text bundled (`LICENSE-genkgo-camt-MIT.txt`) | GREEN | APPROVED |
| Synthetic fixtures (future) | our own | Yes (we own them) | — | GREEN | APPROVED |

## 5. Reference documents (NOT redistributed — facts only)

| Asset | Basis | Class | Decision |
|---|---|---|---|
| Rabobank MT940S format PDF | Copyright Rabobank, "no part may be reproduced" | RED for redistribution / GREEN for reading facts | RESEARCH ONLY — never bundle, never quote verbatim |
| kontopruef.de German MT940 page | Public web page, copyright its author | RESEARCH ONLY | Facts only |
| Bank format guides (Danske, HypoVereinsbank, National-Bank, GS, ABN AMRO) | Public documentation, publisher copyright | RESEARCH ONLY | Facts only |
| SWIFT MT940 message reference (Category 9 handbook) | Proprietary SWIFT documentation | RED | NOT USED — never copy; independent public references used instead |

## 6. Explicitly rejected

| Name | Licence | Reason | Class |
|---|---|---|---|
| jGnash MT940 code | GPLv3 | Copyleft — forbidden in closed-source product; not read, not copied | RED |
| sepaxml (would pull text-unidecode) | MIT + Artistic/GPLv2+ dual dep | Wrong capability anyway; copyleft-flagged transitive dep | RED (as dependency) |
| pain001 | Apache-2.0/MIT | Wrong capability (pain.001 generation, no camt) | REJECTED (not a licence issue) |
| okane | MIT | Czech-dialect-specific, alpha | REJECTED (not a licence issue) |
| pycamt | MIT | Immature; reference reading only | RESEARCH ONLY |
| GPL/AGPL anything | — | Forbidden by policy | RED |

## 7. Audit verdict

- RED items in the build: **0** (policy satisfied).
- AMBER items: PySide6/Qt (LGPL-dynamic), PyInstaller (GPL+exception), ISO 20022 XSDs (notice retention) — all with documented, satisfiable conditions.
- Obligation artefacts required at build time: THIRD-PARTY-NOTICES file (all licences + ISO notice), LGPL/GPLv3 full texts, About-dialog notices, `pip-licenses` CI gate blocking GPL/AGPL.
