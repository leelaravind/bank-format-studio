"""Stable diagnostic codes and the message catalog.

Codes are stable API (GOLDEN-CASE-REQUIREMENTS.md rule 6): golden cases and the GUI
reference codes, never message wording. Human-readable wording lives only here so it
can improve without breaking tests.
"""

from __future__ import annotations

# --- Errors (E_*) -----------------------------------------------------------
E_MT940_BAD_DC_MARK = "E_MT940_BAD_DC_MARK"
E_MT940_MALFORMED_TAG = "E_MT940_MALFORMED_TAG"
E_MT940_MISSING_OPENING = "E_MT940_MISSING_OPENING"
E_MT940_MISSING_CLOSING = "E_MT940_MISSING_CLOSING"
E_MT940_BAD_AMOUNT = "E_MT940_BAD_AMOUNT"
E_MT940_BAD_DATE = "E_MT940_BAD_DATE"
E_MT940_PARSE = "E_MT940_PARSE"
E_BAD_CURRENCY = "E_BAD_CURRENCY"
E_BALANCE_CURRENCY_MISMATCH = "E_BALANCE_CURRENCY_MISMATCH"
E_PAGE_CHAIN_BROKEN = "E_PAGE_CHAIN_BROKEN"
E_CAMT_SCHEMA_INVALID = "E_CAMT_SCHEMA_INVALID"
E_CAMT_UNSUPPORTED_VERSION = "E_CAMT_UNSUPPORTED_VERSION"
E_CAMT_NOT_CAMT053 = "E_CAMT_NOT_CAMT053"
E_XML_NOT_WELL_FORMED = "E_XML_NOT_WELL_FORMED"
E_XML_DTD_FORBIDDEN = "E_XML_DTD_FORBIDDEN"
E_INPUT_TOO_LARGE = "E_INPUT_TOO_LARGE"
E_XLSX_UNSAFE_ARCHIVE = "E_XLSX_UNSAFE_ARCHIVE"
E_CSV_MISSING_COLUMN = "E_CSV_MISSING_COLUMN"
E_CSV_BAD_VALUE = "E_CSV_BAD_VALUE"
E_CSV_INCONSISTENT = "E_CSV_INCONSISTENT"
E_RECON_MISMATCH = "E_RECON_MISMATCH"
E_UNSUPPORTED_CONVERSION = "E_UNSUPPORTED_CONVERSION"
E_ENCODING_UNDECODABLE = "E_ENCODING_UNDECODABLE"
E_INTERNAL = "E_INTERNAL"

# --- Warnings (W_*) ---------------------------------------------------------
W_DUPLICATE_ENTRY = "W_DUPLICATE_ENTRY"
W_CURRENCY_DECIMALS = "W_CURRENCY_DECIMALS"
W_NON_BOOKED_ENTRY = "W_NON_BOOKED_ENTRY"
W_ENTRY_CURRENCY_DIFFERS = "W_ENTRY_CURRENCY_DIFFERS"
W_SUMMARY_MISMATCH = "W_SUMMARY_MISMATCH"
W_DATE_OUT_OF_PERIOD = "W_DATE_OUT_OF_PERIOD"
W_SEQUENCE_GAP = "W_SEQUENCE_GAP"
W_UNKNOWN_TAG = "W_UNKNOWN_TAG"
W_UNKNOWN_BALANCE_TYPE = "W_UNKNOWN_BALANCE_TYPE"
W_ENCODING_FALLBACK = "W_ENCODING_FALLBACK"
W_CHARSET_VIOLATION = "W_CHARSET_VIOLATION"
W_FILENAME_SANITIZED = "W_FILENAME_SANITIZED"
W_ENTRY_DATE_YEAR_GUESSED = "W_ENTRY_DATE_YEAR_GUESSED"
W_IMPOSSIBLE_DATE = "W_IMPOSSIBLE_DATE"
W_BATCH_SUM_MISMATCH = "W_BATCH_SUM_MISMATCH"
W_RESTRICTED_SUBSET_SUSPECTED = "W_RESTRICTED_SUBSET_SUSPECTED"
W_DANGLING_INTERMEDIATE = "W_DANGLING_INTERMEDIATE"
W_REFERENCE_TRUNCATED = "W_REFERENCE_TRUNCATED"

_CATALOG: dict[str, str] = {
    E_MT940_BAD_DC_MARK: "Unrecognized debit/credit mark {value!r} in :61: line — expected C, D, RC or RD ({where}).",
    E_MT940_MALFORMED_TAG: "Cannot parse MT940 field {tag} ({where}): {detail}",
    E_MT940_MISSING_OPENING: "Statement has no opening balance (:60F:/:60M:) — cannot process ({where}).",
    E_MT940_MISSING_CLOSING: "Statement has no closing balance (:62F:/:62M:) — the file appears truncated ({where}).",
    E_MT940_BAD_AMOUNT: "Invalid amount {value!r} ({where}): {detail}",
    E_MT940_BAD_DATE: "Invalid date {value!r} ({where}): {detail}",
    E_MT940_PARSE: "MT940 parsing failed ({where}): {detail}",
    E_BAD_CURRENCY: "Invalid currency code {value!r} ({where}) — expected a 3-letter ISO 4217 code.",
    E_BALANCE_CURRENCY_MISMATCH: "Balance currencies disagree within one statement: {detail} ({where}).",
    E_PAGE_CHAIN_BROKEN: "Statement pages do not chain: closing balance of page {page} ({detail}) does not match the next page's opening balance.",
    E_CAMT_SCHEMA_INVALID: "The file does not conform to the {version} schema: {detail} (at {where}).",
    E_CAMT_UNSUPPORTED_VERSION: "camt.053 version {value!r} is not supported. Supported versions: camt.053.001.02, camt.053.001.08.",
    E_CAMT_NOT_CAMT053: "The XML file is not a camt.053 bank statement (root namespace: {value!r}).",
    E_XML_NOT_WELL_FORMED: "The XML file is not well-formed: {detail}",
    E_XML_DTD_FORBIDDEN: "The XML file contains a DTD or entity definition, which is not allowed for security reasons.",
    E_INPUT_TOO_LARGE: "The input exceeds the configured safety limit ({detail}).",
    E_XLSX_UNSAFE_ARCHIVE: "The .xlsx file failed safety checks ({detail}) and was not opened.",
    E_CSV_MISSING_COLUMN: "Required CSV column {value!r} is missing ({where}).",
    E_CSV_BAD_VALUE: "Invalid value {value!r} in column {column} ({where}): {detail}",
    E_CSV_INCONSISTENT: "CSV data is internally inconsistent: {detail} ({where}).",
    E_RECON_MISMATCH: "Balances do not reconcile: {detail}",
    E_UNSUPPORTED_CONVERSION: "Conversion {detail} is not supported.",
    E_ENCODING_UNDECODABLE: "The file's text encoding could not be determined ({detail}).",
    E_INTERNAL: "Internal error ({detail}). This is a product defect — please report it.",
    W_DUPLICATE_ENTRY: "Possible duplicate transaction: {detail} ({where}).",
    W_CURRENCY_DECIMALS: "Amount {value} has more decimal places than {detail} allows for this currency ({where}).",
    W_NON_BOOKED_ENTRY: "Entry with status {value!r} is not booked; it is excluded from balance reconciliation ({where}).",
    W_ENTRY_CURRENCY_DIFFERS: "Entry currency {value} differs from the account currency {detail} ({where}).",
    W_SUMMARY_MISMATCH: "The statement's own transaction summary disagrees with its entries: {detail}.",
    W_DATE_OUT_OF_PERIOD: "Date {value} lies outside the statement period ({where}).",
    W_SEQUENCE_GAP: "Statement sequence gap: {detail} — a statement may be missing.",
    W_UNKNOWN_TAG: "Unknown/non-standard MT940 tag {value!r} was preserved as additional information ({where}).",
    W_UNKNOWN_BALANCE_TYPE: "Balance type {value!r} is not a known code; carried through unchanged ({where}).",
    W_ENCODING_FALLBACK: "The file is not valid UTF-8; decoded using fallback encoding {value} ({detail}).",
    W_CHARSET_VIOLATION: "Text contains characters outside the SWIFT character set ({where}); they were transliterated or preserved as-is depending on target format.",
    W_FILENAME_SANITIZED: "The derived output filename was sanitized from {value!r} to {detail!r} for safety.",
    W_ENTRY_DATE_YEAR_GUESSED: "Entry (booking) date year is not present in MT940; year {value} was derived from the value date ({where}).",
    W_IMPOSSIBLE_DATE: "Impossible calendar date {value!r} ({where}); {detail}.",
    W_BATCH_SUM_MISMATCH: "Batch entry amount does not equal the sum of its detail transactions: {detail} ({where}).",
    W_RESTRICTED_SUBSET_SUSPECTED: "The file is schema-valid but violates a national subset convention: {detail} ({where}).",
    W_DANGLING_INTERMEDIATE: "Statement {where} starts or ends with an intermediate balance (:60M:/:62M:) but no continuation page was found — the statement may be incomplete.",
    W_REFERENCE_TRUNCATED: "Reference {value!r} exceeds the MT940 16-character limit and was truncated; the full value was preserved in :86: ({where}).",
}


def render(code: str, **params: object) -> str:
    """Render the human-readable message for a diagnostic code."""
    template = _CATALOG.get(code)
    if template is None:
        return f"{code}: {params}" if params else code
    class _Default(dict):
        def __missing__(self, key: str) -> str:
            return "?"
    return template.format_map(_Default(**{k: v for k, v in params.items()}))


class BfsError(Exception):
    """A controlled, user-presentable failure with a stable code."""

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(render(code, **params))
