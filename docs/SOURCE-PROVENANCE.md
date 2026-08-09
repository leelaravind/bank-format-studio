# SOURCE PROVENANCE REGISTER (Task 16)

Authoritative register of every external asset. Access date for all entries: **2026-08-09**.
Rule: every external binary/schema/sample used in any later phase MUST have a row here.

## A. MT940 sample fixtures (local: `sample-data/public/mt940/`)

Source project: WoLpH/mt940 (Rick van Hattem), https://github.com/WoLpH/mt940 — raw files
fetched from `https://raw.githubusercontent.com/WoLpH/mt940/develop/mt940_tests/<path>`.
Redistribution: YES for all, conditional on retaining licence texts (stored in
`references/licences/`, see section C). Suitable as internal development material and,
with notices, for shipping in a test bundle. NOTE (Probe 1/2): most are parse-quality
only — balances do not all reconcile; see `research-probes/PROBE-RESULTS.md`.

| Asset ID | File | Upstream path | Licence | Variant | SHA256 |
|---|---|---|---|---|---|
| MT940-S01 | wolph-mt940-asnb.txt | ASNB/mt940.txt | BSD-3-Clause | ASNB (NL), FIN blocks; needs StatementASNB handler | f6af41ce92fd4591d2d0cb5689f1664a6edf0b172e3ee70b9b3b4d6c3c3b66e8 |
| MT940-S02 | wolph-mt940-jejik-abnamro.sta | jejik/abnamro.sta | MIT (Frank Oxener / Agile Dovadi BV) | ABN AMRO (NL); arithmetically inconsistent (parse-only) | cbec266b057f2130d73ab799ad0bc72e06648dfd96297c6c8a0aa26c21acb2db |
| MT940-S03 | wolph-mt940-jejik-ing.sta | jejik/ing.sta | MIT (Frank Oxener) | ING (NL); tabs + U+00AD chars | 5e1d3f83cc76fb211dbd6a769c8ccb392a3933e63af242ac8dbc848c162f467d |
| MT940-S04 | wolph-mt940-jejik-rabobank-iban.sta | jejik/rabobank-iban.sta | MIT (Frank Oxener) | Rabobank (NL), structured `:86:` | f05d1f83985861d55e24e74a26bb482bf2979fafec1053383cc83fd86f918b88 |
| MT940-S05 | wolph-mt940-betterplace-sepa.sta | betterplace/sepa_snippet.sta | Apache-2.0 (betterplace) | German SEPA GVC | c176e302817ec492a1fd711e2c2daf4e87657763b67c72c33c38f30cdd1a495a |
| MT940-S06 | wolph-mt940-cmxl-german.sta | cmxl/mt940.sta | MIT (Michael Bumann) | German legacy incl. DEM | 9e3fbe0c78b7a6b0f2be40962bfe4381c48d88901803f1d304b2b1367c1d84ee |
| MT940-S07 | wolph-mt940-gv-codes-german.sta | self-provided/gv_codes.sta | BSD-3-Clause | German GVC/DK code words | 21ae31ed5603544443cbd601383209a381d9602bbd08402c70f668297714699f |
| MT940-S08 | wolph-mt940-mbank.sta | mBank/mt940.txt | BSD-3-Clause | mBank (PL), CP1250 chars; reconciles | e4ef5dd042ea429cac3df3abcf5bbb3425efe2254091474c8156b9907dc9aabf |
| MT940-S09 | wolph-mt940-sberbank.sta | sberbank/171011_01234945.sta | BSD-3-Clause | Sberbank Hungary, `:NS:` tags; reconciles | a3414bb20a6241c2bc44f3b5bd3d5749264f44fa9c626b1bc50cfbc6d4e9a1bd |

## B. camt.053 schemas & samples

### B.1 Official XSD schemas (local: `references/camt053/`)

Publisher: ISO 20022 Registration Authority (message contributor: SWIFT; .14 ISTH).
Licence/usage basis: ISO 20022 IPR policy + SWIFTStandards IPR Policy End-User License
Agreement (Sept 2005) — world-wide, royalty-free, non-exclusive licence to use the
standards "to develop software, products or services"; sub-licensing royalty-free;
the schemas themselves may not be sold as a product; attribution retained in
third-party notices. EULA copy stored at
`references/camt053/licensing/SWIFTStandards_LIC_OUT_V5.pdf`
(SHA256 07ce98e523e756121586eaec30ddc6581db44eac3462f91dcd1d04bcdb38d61e).
IPR policy page: https://www.iso20022.org/intellectual-property-rights.

**Provenance caveat:** www.iso20022.org TCP-reset all automated fetches on 2026-08-09;
files are byte-exact Wayback Machine captures (`id_` raw mode) of the official
iso20022.org download URLs. Each verified well-formed, self-contained (0 imports),
correct targetNamespace, and loadable in xmlschema + lxml (Probe 3).
**Owner follow-up:** re-download the three files from iso20022.org in a normal browser
and diff against the SHA256s below (published XSDs are immutable per version).

| Asset ID | File | Original source URL (via Wayback capture) | Version | SHA256 | Redistributable |
|---|---|---|---|---|---|
| CAMT-X01 | camt.053.001.02.xsd | https://www.iso20022.org/message/12706/download (capture 2026-05-19) | camt.053.001.02 | d664afd198d1f36386a14e2bfd0505c80c1291a5357d8132aa6ab5443a6f2f3d | Y — unmodified, with attribution; may not be sold as such |
| CAMT-X02 | camt.053.001.08.xsd | https://www.iso20022.org/message/12736/download (capture 2025-09-10) | camt.053.001.08 | 338e9cb0c9989b5181802a7b773eece070d6815fc9d6483ac0579117bc24ccba | Y — same conditions |
| CAMT-X03 | camt.053.001.14.xsd | https://www.iso20022.org/message/23479/download (capture 2026-04-21) | camt.053.001.14 (latest) | 4115741fcd10b4fc804349f960ac3f14bd88870ef7af51105488a319295cedf4 | Y — reference only for V1 |

### B.2 camt.053 sample files (local: `sample-data/public/camt053/`)

genkgo fixtures pinned to commit `56e047d1599854ca34db0ccabce15230fcdd3f16` of
https://github.com/genkgo/camt (MIT; licence text bundled alongside the fixtures as
`LICENSE-genkgo-camt-MIT.txt`, SHA256 634495f3a8b4dab2d8449a861be92dede16c70352afe68db743e15e9bd9e746e).
All samples validate against the bundled XSDs (Probe 3, 0 failures).

| Asset ID | File | Source | Version | Licence | SHA256 | Redistributable |
|---|---|---|---|---|---|---|
| CAMT-S01 | iso20022org-official-example_camt.053.001.02.xml | https://www.iso20022.org/documents/messages/camt/instances/camt.053.001.02.zip (official example, capture 2014-03-29) | .02 | ISO 20022 IPR (royalty-free) | d50eddff97d88cbd2fdea812e26c11c21e94fa4714961d473aa9be815b6bbc20 | Y — official published example; OPBD+CLBD, 2 credits + 1 debit batch entry, FX counter-value; `Othr` (non-IBAN) account |
| CAMT-S02 | genkgo-camt_v2-minimal-statement_camt.053.001.02.xml | genkgo test/data/camt053.v2.minimal.xml | .02 | MIT | d01db4b370ff8fbc011466921928411c58794d5a3249a64eeb407848eacd6b07 | Y |
| CAMT-S03 | genkgo-camt_v2-all-balance-types_camt.053.001.02.xml | …/camt053.v2.all-balance-types.xml | .02 | MIT | 51f8fa3ca2ff548a4d98b4633e2483619e8d5f1056f9d22504d9b5a96b97e66e | Y — multiple balance types |
| CAMT-S04 | genkgo-camt_v2-multiple-statements_camt.053.001.02.xml | …/camt053.v2.multi.statement.xml | .02 | MIT | 4c50c6601224e21234c66fe155b1b49e895a7645846c04263d4505c82c5c58bb | Y |
| CAMT-S05 | genkgo-camt_v2-five-decimal-amounts_camt.053.001.02.xml | …/camt053.v2.five.decimals.xml | .02 | MIT | e5d8b3486203e6c342d33a8f22835f3ebd4c9fb16602cc31919fe707a234892c | Y — amount-precision edge |
| CAMT-S06 | genkgo-camt_v2-party-ids-remittance_camt.053.001.02.xml | …/camt053.v2.with-party-ids.xml | .02 | MIT | ec93547fadef45fff52a303e6fd6ef3e574322ab5172deee7628a8a999c4e5f3 | Y — parties + remittance |
| CAMT-S07 | genkgo-camt_v8-statement_camt.053.001.08.xml | …/camt053.v8.xml | .08 | MIT | 792e05f38125ef6d7fe447623c1703b5968ffd1cad9630479a8d588392c8b9b1 | Y — v8 with RmtInf |

### B.3 camt.053 samples verified but NOT downloaded (licence unclear — reference only)

- Goldman Sachs Developer camt.053 US sample (developer.gs.com) — proprietary docs, no reuse licence.
- Bank of America camt.053 reference guide with embedded samples — copyrighted bank documentation.
- SWIFT MyStandards CBPR+ sample instances — login-only, restrictive terms; skipped.
- Deutsche Bank / DZ Bank ISO 20022 migration guides — bank-proprietary, no reuse rights stated.
- CBPR+ usage-guideline PDFs (Clearstream mirrors) — used as version-landscape evidence only; no content copied.

## C. Licence texts (local: `references/licences/`)

| Asset ID | File | Covers | Source |
|---|---|---|---|
| LIC-01 | mt940-python-BSD-3-Clause.txt | mt-940 library + its own fixtures (MT940-S01, S07, S08, S09) | github.com/WoLpH/mt940 LICENSE |
| LIC-02 | mt940-jejik-fixtures-MIT.txt | jejik-corpus fixtures (MT940-S02..S04) | mt940_tests/jejik licence, Frank Oxener |
| LIC-03 | mt940-betterplace-fixtures-Apache-2.0.txt | betterplace fixture (MT940-S05) | mt940_tests/betterplace licence |
| LIC-04 | mt940-cmxl-fixtures-MIT.txt | cmxl fixture (MT940-S06) | mt940_tests/cmxl licence, Michael Bumann |

## D. Reference documents (NOT stored in repo — facts only, no redistribution)

| Asset ID | Reference | Publisher | Purpose | Redistribution |
|---|---|---|---|---|
| REF-01 | Rabobank MT940S Structured format PDF v3.331 | Rabobank | `:61:`/`:86:` subfield semantics, RD/RC, code words | **NO — copyright restricted** |
| REF-02 | kontopruef.de/mt940s.shtml | kontopruef.de | German DK `:86:` GVC `?` subfield map | NO (facts only) |
| REF-03 | sepaforcorporates.com MT940 overview | SEPA for Corporates | Tag overview, notation | NO (facts only) |
| REF-04 | HypoVereinsbank SEPA GVC/return-code PDF | UniCredit/HVB | GVC tables | NO (facts only) |
| REF-05 | National-Bank AG swift_mt940.pdf | National-Bank AG | MultiCash German structure | NO (facts only) |
| REF-06 | GS developer MT940 GVC intro | Goldman Sachs | DFÜ agreement context | NO (facts only) |
| REF-07 | Danske Bank mt940_extended.pdf | Danske Bank | Extended guide — **URL recorded, fetch failed (TLS), unverified** | NO |
| REF-08 | hettwer-beratung.de GVC page | Hettwer Beratung | SEPA GVC in field 86 | NO (facts only) |
| REF-09 | ABN AMRO SEPA downloads index | ABN AMRO | MT94x Formatenboek pointer | NO (facts only) |
| REF-10 | en.wikipedia.org/wiki/MT940 | Wikipedia | Context/positioning | CC BY-SA (not copied) |

## E. Tooling / library provenance (evaluation only in Phase 0)

PyPI packages verified 2026-08-09 (versions + licences in docs/DEPENDENCY-EVALUATION.md):
mt-940 5.0.0, lxml 6.1.1, xmlschema 4.3.2, elementpath 5.1.4, defusedxml 0.7.1,
openpyxl 3.1.5, et-xmlfile 2.0.0 — installed only into a disposable probe venv
outside the repository; nothing vendored.
