# Bank Statement Format Studio 1.0.0 — Supported Formats & Limitations

Publisher: Leela Aravind Karlapudi (ITISYOU) · Support: support@itisyou.app

## Formats the application reads

| Format | Details |
|---|---|
| MT940 | SWIFT customer statement messages (`.sta`, `.mt940`, `.940`, `.txt`) |
| ISO 20022 camt.053 | `camt.053.001.02` and `camt.053.001.08` XML, validated against the official ISO 20022 schemas (bundled — validation works offline) |
| CSV | Only the application's own documented CSV dialect (see `CSV-DIALECT.md`); a CSV import always needs the matching pair of `…transactions.csv` and `…statements.csv` files |

## Formats the application writes

| Format | Details |
|---|---|
| MT940 | Generated output is re-parsed and balance-checked before it is handed to you |
| camt.053.001.02 / camt.053.001.08 | Generated XML is validated against the official schema before saving |
| CSV | The documented two-file dialect (`…transactions.csv` + `…statements.csv`) |
| Excel (XLSX) | **Export only** — the application does not read XLSX files |

## What every conversion includes

- **Validation** of the input file, with clear diagnostics.
- **Balance reconciliation**: opening balance + credits − debits is checked
  against the declared closing balance for every statement, before and after
  conversion.
- **Information-loss report**: the supported formats are not equally
  expressive, so a conversion may change or drop details. Every conversion
  lists exactly which fields were changed, dropped or approximated — the
  application never claims a conversion is lossless.

## Limitations (V1)

- Windows only (64-bit Windows 10 1809+ / Windows 11).
- Other camt.053 versions (for example `.001.14`) and other statement
  formats (CAMT.052/054, BAI2, OFX/QIF, PDF statements) are not supported.
- XLSX is an export format only.
- CSV import accepts only the documented dialect — arbitrary bank CSV
  exports are not accepted (this is what makes validation and
  reconciliation trustworthy).
- Fully offline by design: there is no cloud service, no telemetry and no
  auto-update. New versions are delivered as new installers.
- The application converts and reports on statement files. It is not
  banking, accounting, tax, legal or financial advice, and it makes no
  automated financial decisions.
