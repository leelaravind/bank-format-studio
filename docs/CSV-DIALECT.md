# Bank Statement Format Studio — CSV Interchange Format (dialect v1.1)

This document describes the CSV files Bank Statement Format Studio writes and the
only CSV layout it reads back. It ships with the application so you can build or
edit files that the converter will accept.

## Files

Every CSV export produces **two files** that belong together:

- `…transactions.csv` — one row per money movement
- `…statements.csv` — one row per statement, with the declared balances and totals

Both files are always written; both are needed for import.

## Encoding and formatting

- UTF-8 **with BOM**, CRLF line endings, comma delimiter, `"` quoting (RFC 4180).
- Decimal amounts use a dot (`1234.56`), no thousands separators.
- Dates are ISO `YYYY-MM-DD`. Booleans are `true`/`false`.
- Column names are `snake_case` and must appear in the header row.

## Statement identity (v1.1)

Banks reuse statement references, so a statement is identified by the pair
**(`statement_id`, `statement_occurrence`)**. `statement_occurrence` is a 1-based
counter added by the exporter — it is a file-local disambiguator, not bank data.
Files without this column can be imported only while every `statement_id` is
unique; otherwise the import stops with a clear error.

## transactions.csv columns

Required: `statement_id`, `account_iban`, `account_other_id`, `statement_number`,
`sequence_number`, `currency`, `booking_date`, `value_date`, `amount` (signed:
credits positive, debits negative), `credit_debit` (`C`/`D`, must match the
amount's sign), `reversal`, `transaction_type_code`, `customer_reference`
(`NONREF` is kept verbatim), `bank_reference`, `remittance_info`.

Optional: `end_to_end_id`, `mandate_id`, `purpose_code`, `creditor_reference`,
`counterparty_name`, `counterparty_account`, `counterparty_bic`, `btc_domain`,
`btc_family`, `btc_subfamily`, `funds_code`, `supplementary_details`,
`entry_reference` (rows sharing a non-empty value form one batch entry),
`instructed_amount`, `instructed_currency`, `exchange_rate`, `charges_amount`,
`status` (`BOOK`/`PDNG`/`INFO`), `additional_info`.

Derived (written by the exporter, validated but not trusted on import):
`row_number`, `statement_occurrence`, `statement_opening_balance`,
`statement_closing_balance`.

## statements.csv columns

`statement_id`, `statement_occurrence`, `account_iban`, `account_other_id`,
`statement_number`, `sequence_number`, `currency`, `opening_balance_date`,
`opening_balance` (signed), `closing_balance_date`, `closing_balance` (signed),
`closing_available_balance`, `total_credits`, `total_debits`, `credit_count`,
`debit_count`, `transaction_count`, `source_format`, `information_loss_flags`.

The balances are the statement's **declared** figures. On conversion the
application recomputes totals from the rows and reports any mismatch — it never
"fixes" balances.

## Excel safety

By default, text cells beginning with `=`, `+`, `-`, `@`, TAB or CR are prefixed
with an apostrophe so spreadsheets treat them as text, never as formulas
(numeric amount columns are exempt). The apostrophe is removed again on import.
A strict RFC mode without this guard is available for machine-to-machine use.

## Known limitations

CSV is a flat projection: multi-line remittance is joined into one field,
structured invoice details are reduced to `creditor_reference`, forward/interim
balance types and the bank's own summary block are not exported (the computed
totals in statements.csv replace them), and batch entries are exploded to one
row per underlying transaction (regrouped on import via `entry_reference`).
Every such reduction is listed in the conversion's information-loss report.
