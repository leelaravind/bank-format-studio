# CSV FORMAT STRATEGY (V1 interchange format)

Status: PHASE 0 RESEARCH — proposal only, no implementation.
Date: 2026-08-09

## 1. Design goals

Human-readable, Excel-friendly, deterministic, documented, reconstructable-where-possible.
CSV is a **flat projection of the normalized model** (see DATA-MAPPING-RESEARCH.md);
it is explicitly NOT claimed to preserve every MT940/camt.053 field.

## 2. File model

**One statement export = one transactions CSV** with statement-level fields repeated
on every row (Excel-friendly: filterable, pivotable, no multi-section parsing).
An optional companion **statements summary CSV** (one row per statement) carries
balances and totals. Rationale: multi-section single files ("metadata block then
rows") break Excel sorting and naive CSV tooling; two flat files are simpler and
deterministic.

- Encoding: UTF-8 **with BOM** (required for Excel to detect UTF-8), CRLF line endings.
- Delimiter: comma; fields quoted per RFC 4180 when containing delimiter/quote/newline.
  (Excel locale issues with semicolon-delimited variants: import guidance documented,
  no locale-dependent output.)
- Decimal separator: dot. Dates: ISO 8601 `YYYY-MM-DD`. No thousands separators.
- Deterministic column order and row order (statement order, then entry order as parsed).
- Amounts: signed decimal in `amount` (+credit / −debit) plus explicit `credit_debit`
  column so no consumer must infer sign conventions.
- Formula-injection guard: any cell beginning with `=`, `+`, `-`, `@`, TAB or CR is
  prefixed with `'` on export **only in "Excel-safe" mode (default ON)**; a strict
  RFC mode without mangling is available for machine round-trips. (Signed negative
  amounts are exempt from the `-` rule — numeric-only cells are safe.)
  See SECURITY-REQUIREMENTS.md.

## 3. transactions.csv columns

REQUIRED (always present, may be empty only where noted):
| Column | Notes |
|---|---|
| `statement_id` | from :20: / Stmt/Id |
| `account_iban` or `account_other_id` | at least one non-empty |
| `statement_number` | :28C: / LglSeqNb |
| `sequence_number` | may be empty |
| `currency` | statement/account currency, ISO 4217 |
| `booking_date` | may be empty (MT940 optional subfield) |
| `value_date` | |
| `amount` | signed, dot decimal |
| `credit_debit` | `C`/`D` |
| `reversal` | `true`/`false` |
| `transaction_type_code` | SWIFT 4-char or camt proprietary code |
| `customer_reference` | `NONREF` normalized to empty + `nonref=true`? — DECISION PENDING, see §5 |
| `bank_reference` | |
| `remittance_info` | unstructured lines joined with a single space; original line breaks lost (documented) |

OPTIONAL (present as columns, often empty):
`end_to_end_id`, `mandate_id`, `purpose_code`, `creditor_reference`,
`counterparty_name`, `counterparty_account`, `counterparty_bic`,
`btc_domain`, `btc_family`, `btc_subfamily`, `funds_code`,
`supplementary_details`, `entry_reference`, `instructed_amount`,
`instructed_currency`, `exchange_rate`, `charges_amount`, `status`,
`additional_info`.

DERIVED (computed, never parsed back as authoritative):
`row_number`, `signed_amount_in_account_currency`, `statement_opening_balance`,
`statement_closing_balance` (repeated per row for spreadsheet convenience —
marked derived so CSV→MT940/camt reconstruction validates them against the
summary file rather than trusting per-row repetition).

## 4. statements.csv columns (summary companion)

`statement_id`, `account_iban`/`account_other_id`, `statement_number`,
`sequence_number`, `currency`, `opening_balance_date`, `opening_balance`,
`closing_balance_date`, `closing_balance`, `closing_available_balance`,
`total_credits`, `total_debits`, `credit_count`, `debit_count`,
`transaction_count`, `source_format`, `information_loss_flags`.

## 5. Documented lossy behaviour (explicit)

- `:86:`/remittance line-break layout collapsed to single-line text.
- Structured remittance (invoice document lists) reduced to `creditor_reference`.
- Charges breakdown reduced to a single `charges_amount`.
- Batch entries: one row per `TxDtls` with shared `entry_reference`; the Ntry-level
  aggregate is reconstructable only by grouping.
- Multiple FWAV balances: only in statements.csv as a joined `forward_balances`
  field if at all (DECISION PENDING).
- CSV → MT940/camt.053 is "reconstruction from core fields": output is valid and
  balance-consistent but cannot resurrect structure the CSV never carried.

## 6. Open decisions — RESOLVED in spec/IMPLEMENTATION-PLAN.md §2 (2026-08-09)

1. `NONREF`: passed through verbatim; empty cell = absent.
2. XLSX export = straight rendering of the same two tables as worksheets; no report sheet in V1.
3. Column names: `snake_case` confirmed.
4. `statements.csv`: mandatory on every export; no single-file mode in V1.
