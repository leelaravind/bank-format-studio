# RESEARCH PROBE RESULTS

Date: 2026-08-09. Probes are disposable verification scripts, not product code.
Probe environment: Python 3.14.0 venv (outside the repo) with mt-940 5.0.0,
lxml 6.1.1, xmlschema 4.3.2 (+elementpath 5.1.4), defusedxml 0.7.1, openpyxl 3.1.5
— all installed cleanly on Python 3.14 / Windows 11.

## Probe 1 — `probe_mt940_parse.py` (mt-940 library vs collected fixtures)

| Fixture | Result |
|---|---|
| wolph-mt940-asnb.txt | FAILS with default parser — **requires the library's `StatementASNB` bank-variant tag handler** (see Probe 2) |
| wolph-mt940-betterplace-sepa.sta | parses: 11 tx, EUR, German GVC `:86:` handled |
| wolph-mt940-cmxl-german.sta | parses: 16 tx (multi-statement file, 3 accounts) |
| wolph-mt940-gv-codes-german.sta | parses: 2 tx; **no closing balance in fixture** |
| wolph-mt940-jejik-abnamro.sta | parses: 10 tx across 2 statement pages |
| wolph-mt940-jejik-ing.sta | parses: 7 tx despite tabs/soft-hyphen chars |
| wolph-mt940-jejik-rabobank-iban.sta | parses: 4 tx, IBAN account, structured `:86:` |
| wolph-mt940-mbank.sta | parses: 3 tx; **movements reconcile exactly against declared balances** |
| wolph-mt940-sberbank.sta | parses: 3 tx incl. `:NS:` tags; **reconciles exactly** |

## Probe 2 — `probe_mt940_asnb.py` (bank-variant mechanism + reconciliation reality)

- ASNB fixture parses successfully once `mt940.tags.StatementASNB` is registered —
  confirms the library's documented bank-variant processor mechanism works and that
  our product will need a **variant profile selection** layer on top of it.
- The ABN AMRO fixture is **arithmetically inconsistent by construction**: statement 1
  declares opening C 3236,28 → closing C 876,84 (delta −2359,44) but its movements sum
  to −321,44; page 2's `:60M:` (2876,84) does not chain from page 1's `:62F:` (876,84).

## Conclusions carried into the source pack

1. mt-940 5.0.0 installs and runs on Python 3.14 (not yet declared in its classifiers) —
   CI verification requirement stands but no blocker found.
2. The bank-variant mechanism (custom tags/processors) is real and needed — default
   parsing alone does not cover all collected variants.
3. **Public fixtures are parse-quality, not reconciliation-quality.** Several
   (abnamro, ing, rabobank, cmxl, betterplace) have balances that do not reconcile
   with their movements, or omit closing balances. They are suitable for parser
   robustness testing only. Golden reconciliation cases must therefore be SYNTHETIC
   (built to satisfy INV-1 by construction) — this is now a stated requirement in
   FIXTURE-PLAN.md / GOLDEN-CASE-REQUIREMENTS.md.
4. mbank + sberbank fixtures do reconcile and can serve as public-derived
   reconciliation smoke cases.

## Probe 3 — `probe_camt_validate.py` (XSD load + validation)

Run 2026-08-09 after ISO 20022 asset collection. Results:

- All three collected XSDs (camt.053.001.02, .08, .14) load successfully in **both**
  `xmlschema` 4.3.2 and `lxml` 6.1.1 (`etree.XMLSchema`), each declaring the expected
  `urn:iso:std:iso:20022:tech:xsd:camt.053.001.0X` targetNamespace, self-contained
  (no imports/includes) — confirming fully-offline schema resolution is trivial.
- All 7 collected samples validate: 6 × camt.053.001.02 (incl. the official ISO
  example instance, all-balance-types, multi-statement, 5-decimal amounts,
  party-ids/remittance) and 1 × camt.053.001.08. **0 failures.**
- Validation ran with a hardened lxml parser (`resolve_entities=False,
  no_network=True, dtd_validation=False`) — no issues, confirming the
  SEC-13 posture is compatible with real files.

**Overall probe verdict: the source pack is internally consistent and usable.**
