"""The documented V1 CSV interchange dialect (CSV-FORMAT-STRATEGY.md, locked decisions).

Two files per export: transactions.csv + statements.csv (mandatory pair).
UTF-8 with BOM, CRLF, comma delimiter, dot decimals, ISO dates, snake_case columns.
Excel-safe formula neutralization is ON by default; strict RFC mode available.
"""

from __future__ import annotations

TRANSACTIONS_REQUIRED = [
    "statement_id", "account_iban", "account_other_id", "statement_number",
    "sequence_number", "currency", "booking_date", "value_date",
    "amount", "credit_debit", "reversal", "transaction_type_code",
    "customer_reference", "bank_reference", "remittance_info",
]
TRANSACTIONS_OPTIONAL = [
    "end_to_end_id", "mandate_id", "purpose_code", "creditor_reference",
    "counterparty_name", "counterparty_account", "counterparty_bic",
    "btc_domain", "btc_family", "btc_subfamily", "funds_code",
    "supplementary_details", "entry_reference", "instructed_amount",
    "instructed_currency", "exchange_rate", "charges_amount", "status",
    "additional_info",
]
TRANSACTIONS_DERIVED = [
    "row_number", "statement_occurrence", "statement_opening_balance",
    "statement_closing_balance",
]
# Required statement columns (unchanged since dialect v1.0 — statement_occurrence
# is optional for backward compatibility, but REQUIRED when statement_ids repeat).
STATEMENTS_REQUIRED = [
    "statement_id", "account_iban", "account_other_id", "statement_number",
    "sequence_number", "currency", "opening_balance_date", "opening_balance",
    "closing_balance_date", "closing_balance",
]
# Dialect v1.1 (B-2): `statement_occurrence` is a DERIVED 1-based ordinal that
# distinguishes multiple statements sharing one statement_id (banks reuse :20:
# references). It is a file-local disambiguator, NOT bank data: rows with the
# same (statement_id, statement_occurrence) belong to one statement occurrence.
# Files without the column remain readable when statement_ids are unique.
TRANSACTIONS_COLUMNS = TRANSACTIONS_REQUIRED + TRANSACTIONS_OPTIONAL + TRANSACTIONS_DERIVED

STATEMENTS_COLUMNS = [
    "statement_id", "statement_occurrence", "account_iban", "account_other_id", "statement_number",
    "sequence_number", "currency", "opening_balance_date", "opening_balance",
    "closing_balance_date", "closing_balance", "closing_available_balance",
    "total_credits", "total_debits", "credit_count", "debit_count",
    "transaction_count", "source_format", "information_loss_flags",
]

# Excel-safe neutralization (SEC-16): prefix these leading characters with an
# apostrophe in text cells. '-' is only neutralized in non-numeric cells; numeric
# amount columns are exempt by construction (they are emitted as plain numbers).
FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
NUMERIC_COLUMNS = {
    "amount", "instructed_amount", "exchange_rate", "charges_amount",
    "opening_balance", "closing_balance", "closing_available_balance",
    "total_credits", "total_debits", "statement_opening_balance",
    "statement_closing_balance",
}


def neutralize(value: str, column: str, excel_safe: bool) -> str:
    if not excel_safe or not value or column in NUMERIC_COLUMNS:
        return value
    if value[0] in FORMULA_TRIGGERS:
        return "'" + value
    return value


def deneutralize(value: str) -> str:
    """Inverse of `neutralize` on import: a leading apostrophe guarding a trigger
    character is an artefact of Excel-safe mode, not data."""
    if len(value) >= 2 and value[0] == "'" and value[1] in FORMULA_TRIGGERS:
        return value[1:]
    return value
