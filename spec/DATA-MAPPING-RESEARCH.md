# DATA MAPPING RESEARCH — Normalized Model for MT940 ↔ camt.053 ↔ CSV

Status: PHASE 0 RESEARCH — no implementation.
Date: 2026-08-09

This document defines the candidate normalized internal model that bridges MT940,
ISO 20022 camt.053 and the V1 CSV interchange format, and records — field by field —
where information survives conversion and where it does not.

**Headline finding: fully lossless bidirectional conversion between MT940 and
camt.053 is NOT possible.** camt.053 is a strict superset in expressiveness
(structured parties, structured remittance, per-entry currency/exchange data,
charge breakdowns, batch entries). MT940 carries a small number of fields camt.053
has no first-class slot for (funds code, free-form supplementary details layout,
the exact :86: byte layout). The product must therefore be honest: conversions are
**semantically faithful with documented loss**, never "lossless" as a blanket claim.

---

## 1. Candidate normalized model

### 1.1 Statement (one per MT940 message page-set / one per camt.053 `Stmt` block)

| Field | Type | Req | MT940 source | camt.053 source/destination | CSV representation |
|---|---|---|---|---|---|
| `statement_id` | string | REQ | `:20:` Transaction Reference | `Stmt/Id` | `statement_id` column |
| `related_reference` | string | OPT | `:21:` | no direct slot (note in `AddtlStmtInf`) | `related_reference` |
| `account_id` | struct | REQ | `:25:` (free text: BIC/account or IBAN) | `Stmt/Acct/Id/IBAN` or `Stmt/Acct/Id/Othr/Id` | `account_iban` / `account_other_id` |
| `account_currency` | ISO 4217 | REQ | currency of `:60F:` (implied statement-wide) | `Stmt/Acct/Ccy` and/or balance `Amt/@Ccy` | `currency` |
| `statement_number` | int | REQ | `:28C:` before `/` | `Stmt/LglSeqNb` | `statement_number` |
| `sequence_number` | int | OPT | `:28C:` after `/` | `Stmt/ElctrncSeqNb` (approximate match) | `sequence_number` |
| `creation_datetime` | datetime | OPT | none (derive) | `GrpHdr/CreDtTm` (REQ in camt) | `created_at` |
| `from_datetime` / `to_datetime` | datetime | OPT | none | `Stmt/FrToDt` | `period_from`, `period_to` |
| `opening_balance` | Balance | REQ | `:60F:` (or `:60M:` on continuation pages) | `Bal` with `Tp/CdOrPrtry/Cd = OPBD` | header/summary columns |
| `closing_balance` | Balance | REQ | `:62F:` (or `:62M:`) | `Bal` with `Cd = CLBD` | header/summary columns |
| `closing_available_balance` | Balance | OPT | `:64:` | `Bal` with `Cd = CLAV` | optional summary column |
| `forward_available_balances` | Balance[] | OPT | `:65:` (repeatable) | `Bal` with `Cd = FWAV` (repeatable) | optional summary columns |
| `transactions` | Transaction[] | REQ (may be empty) | `:61:`(+`:86:`) repetitions | `Ntry` repetitions | one CSV row each |
| `additional_info` | string | OPT | trailing `:86:` after last `:62F:` (bank-specific) | `Stmt/AddtlStmtInf` | `statement_additional_info` |

### 1.2 Balance (value object)

| Field | Type | Req | MT940 | camt.053 | CSV |
|---|---|---|---|---|---|
| `credit_debit` | enum C/D | REQ | subfield 1 of `:60F:/:62F:/:64:/:65:` | `CdtDbtInd` | sign of the decimal value |
| `date` | date | REQ | YYMMDD subfield | `Dt/Dt` | ISO `YYYY-MM-DD` |
| `currency` | ISO 4217 | REQ | 3-char subfield | `Amt/@Ccy` | `currency` |
| `amount` | decimal ≥ 0 | REQ | comma-decimal, ≤15 digits | `Amt` (dot decimal) | signed dot decimal |

Normalized storage decision to research further: store `amount` as **unsigned decimal +
explicit C/D flag** (matches both formats natively) and derive signed values only at
CSV boundaries. Never use binary floating point; `decimal.Decimal` semantics required.

### 1.3 Transaction / Entry

| Field | Type | Req | MT940 source (`:61:` subfields / `:86:`) | camt.053 (`Ntry`/`NtryDtls/TxDtls`) | CSV | Loss risk |
|---|---|---|---|---|---|---|
| `value_date` | date | REQ | `:61:` sf1 YYMMDD | `Ntry/ValDt/Dt` | `value_date` | none (century pivot rule needed for YY) |
| `booking_date` | date | OPT | `:61:` sf2 MMDD (no year!) | `Ntry/BookgDt/Dt` | `booking_date` | **MT940 entry date lacks a year — must be derived from value date with a documented year-boundary heuristic** |
| `credit_debit` | enum C/D | REQ | `:61:` sf3 (`C`,`D`,`RC`,`RD`, opt. `E` prefixed variants) | `Ntry/CdtDbtInd` | sign of `amount` | reversal flag must be carried separately |
| `is_reversal` | bool | REQ (default false) | `RC`/`RD` marks | `Ntry/RvslInd` | `reversal` column | semantics differ subtly: MT940 `RD` = reversal of a debit (movement is credit-direction); mapping must be explicit |
| `funds_code` | char | OPT | `:61:` sf4 (3rd char of currency) | **no slot** → `AddtlNtryInf` note | `funds_code` (optional) | **LOSSY toward camt** |
| `amount` | decimal | REQ | `:61:` sf5 comma-decimal | `Ntry/Amt` + `@Ccy` | `amount` | MT940 has no per-transaction currency; camt→MT940 with per-entry currency ≠ account currency **cannot be represented** |
| `swift_tx_type` | string(4) | REQ in MT940 | `:61:` sf6 (`N`/`F` + 3 chars, e.g. `NTRF`, `NMSC`) | `Ntry/BkTxCd/Prtry/Cd` (as proprietary) | `transaction_type_code` | camt's structured `Domn/Fmly/SubFmlyCd` ↔ SWIFT codes is a **many-to-many mapping**; round trip only via proprietary carry-through |
| `bank_tx_domain_code` | string | OPT | none | `Ntry/BkTxCd/Domn/Cd` + `Fmly/Cd` + `SubFmlyCd` | `btc_domain`,`btc_family`,`btc_subfamily` | **LOSSY toward MT940** (no slot; best-effort SWIFT-code mapping table, else default `NMSC`) |
| `customer_reference` | string(16) | REQ in MT940 | `:61:` sf7 (before `//`), `NONREF` when absent | `TxDtls/Refs/EndToEndId` (closest) or `Refs/Ref` | `customer_reference` | EndToEndId is 35 chars; >16 chars **cannot fit** MT940 sf7 — truncation or `:86:` spillover required |
| `bank_reference` | string(16) | OPT | `:61:` sf8 (after `//`) | `Ntry/AcctSvcrRef` or `TxDtls/Refs/AcctSvcrRef` | `bank_reference` | length mismatch (camt 35 vs MT940 16) |
| `supplementary_details` | string(34) | OPT | `:61:` sf9 (next line) | **no dedicated slot** → `AddtlNtryInf` | `supplementary_details` | **LOSSY toward camt** (concatenated into free text) |
| `end_to_end_id` | string(35) | OPT | only if bank encodes `EREF` in structured `:86:` | `TxDtls/Refs/EndToEndId` | `end_to_end_id` | MT940 support depends on bank's `:86:` convention |
| `mandate_id` | string | OPT | `MARF`/structured `:86:` only | `TxDtls/Refs/MndtId` | `mandate_id` | same dependency |
| `counterparty_name` | string | OPT | inside `:86:` (convention-specific) | `TxDtls/RltdPties/Cdtr|Dbtr/(Pty/)Nm` | `counterparty_name` | **MT940 has no structured slot** — extraction is heuristic per bank; writing MT940 flattens into `:86:` |
| `counterparty_account` | IBAN/other | OPT | inside `:86:` | `TxDtls/RltdPties/CdtrAcct|DbtrAcct/Id` | `counterparty_account` | same |
| `counterparty_bic` | BIC | OPT | inside `:86:` | `TxDtls/RltdAgts/.../BICFI` | `counterparty_bic` | same |
| `remittance_unstructured` | string[] | OPT | `:86:` free text (6×65 chars max) | `TxDtls/RmtInf/Ustrd` (repeatable, 140 chars each) | `remittance_info` | **camt→MT940 truncation risk beyond 390 usable chars**; layout/line-break fidelity lost |
| `remittance_structured` | struct | OPT | `SCOR`-type refs in structured `:86:` only | `TxDtls/RmtInf/Strd` (creditor ref, invoice docs) | `creditor_reference` (partial) | **LOSSY toward MT940 and CSV** — Strd can hold invoice lists; CSV keeps only the creditor reference |
| `purpose_code` | ext. code | OPT | `PURP` in structured `:86:` only | `TxDtls/Purp/Cd` | `purpose_code` | bank-convention-dependent |
| `return_reason` | code | OPT | `RTRN`-style `:86:` conventions | `TxDtls/RtrInf/Rsn/Cd` | `return_reason` | lossy/heuristic |
| `charges` | struct[] | OPT | `CHGS` in `:86:` (rare) | `Ntry/Chrgs` or `TxDtls/Chrgs` (amount+type breakdown) | `charges_amount` (single total only) | **LOSSY toward MT940 and CSV** |
| `instructed_amount` + `exchange` | struct | OPT | `OCMT`/`EXCH` in `:86:` (bank-specific) | `TxDtls/AmtDtls/InstdAmt` + `CcyXchg` | `instructed_amount`,`instructed_currency`,`exchange_rate` | representable both ways only where bank uses OCMT convention |
| `batch_info` | struct | OPT | not representable (one `:61:` = one movement) | `Ntry` may contain `NtryDtls/Btch` + many `TxDtls` | **CSV: one row per TxDtls with `entry_ref` grouping** | **camt batch entries CANNOT round-trip through MT940** — a batched Ntry must either stay one aggregate line or be exploded, both lossy |
| `entry_reference` | string | OPT | none | `Ntry/NtryRef` | `entry_reference` | lossy toward MT940 |
| `status` | code | REQ (assume BOOK) | implied booked | `Ntry/Sts` (BOOK in camt.053 practice; schema also allows PDNG/INFO) | `status` | non-BOOK entries have no MT940 representation — must warn/drop |
| `additional_entry_info` | string | OPT | overflow bucket from `:86:` | `Ntry/AddtlNtryInf` | `additional_info` | serves as the designated loss-capture field |
| `raw_86` | string | internal | verbatim `:86:` content | n/a (kept in model for audit) | optional `raw_details` column | keep to enable audit + best-effort re-emission |

### 1.4 Fields that CANNOT be perfectly round-tripped (critical list)

**MT940 → camt.053 → MT940** (near-round-trippable, with care):
1. `:86:` byte-exact layout — line breaks and bank-specific separators are not preserved once parsed into `Ustrd`/party fields. Mitigation: carry `raw_86` internally; document that re-emitted `:86:` is normalized.
2. Funds code (sf4) and supplementary details (sf9) — survive only as annotations in `AddtlNtryInf`; a foreign camt file (not produced by us) will not have them.
3. Entry-date year — regenerated from heuristic, identical in practice except at year boundaries; must be tested explicitly.

**camt.053 → MT940** (structurally lossy — must be documented per conversion):
1. Structured parties (names, IBANs, BICs, addresses) — flattened into `:86:` text, structure lost unless a structured-`:86:` convention (e.g. `/EREF/`, German GVC `?20..?`) is chosen as output style.
2. Structured remittance (`Strd`, invoice references) — only creditor reference survives, as text.
3. Bank transaction code Domain/Family/SubFamily — degraded to a 4-char SWIFT code via mapping table, default `NMSC`.
4. References longer than 16 chars (`EndToEndId`, `AcctSvcrRef` at 35 chars) — truncated in `:61:`, full value spilled to `:86:`.
5. Batch entries with multiple `TxDtls` — no MT940 equivalent.
6. Charges breakdown, exchange-rate details, multiple `Prtry` balance types, `PDNG` entries, per-entry currencies ≠ account currency — dropped or aggregated, with mandatory warnings.
7. Character set — camt UTF-8 content must be transliterated to the SWIFT X character set; accented/non-Latin characters are lossy.

**Anything → CSV**: CSV is a flat projection. It can round-trip the normalized
*core* (dates, amounts, C/D, references, counterparty triple, unstructured
remittance as one joined string) but not nested structures (Strd remittance,
charges breakdown, batch TxDtls, multiple FWAV balances). CSV → MT940/camt is
therefore "reconstruction from core fields", flagged as such.

---

## 2. Consequences for product claims

- Allowed claim: "converts MT940 ↔ camt.053 ↔ CSV with balance-verified fidelity
  and explicit information-loss reporting".
- Forbidden claim: "lossless round-trip conversion".
- Every conversion must emit an **information-loss report** (which fields were
  dropped, truncated, transliterated, or heuristically derived). This is a V1
  requirement, not a nice-to-have, and is reflected in golden-case structure
  (`EXPECTED INFORMATION-LOSS NOTES`).

## 3. Open items to confirm against collected sources

- [ ] Confirm `:61:` D/C mark full value set (C, D, RC, RD; some references list `EC/ED` expected marks for MT942 only) against at least two independent public references.
- [ ] Confirm camt.053.001.02 vs .001.08 element differences that affect the model (e.g. `Pty` wrapper introduced for parties in later versions, `RvslInd` availability — verify in downloaded XSDs).
- [ ] Confirm `:28C:` sequence semantics vs `LglSeqNb`/`ElctrncSeqNb` mapping against public bank guides.
- [ ] Decide V1 structured-`:86:` output convention (candidates: SWIFT-style `/EREF/.../REMI/...` vs German GVC `?nn` subfields) after reviewing collected bank variant evidence.
