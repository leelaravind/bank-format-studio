"""XLSX export: the same two tables as the CSV dialect, as two worksheets.

Locked decision: a straight rendering — `transactions` and `statements` sheets,
identical columns, native number/date cells for numeric/date columns, no report
sheet. Text cells go through the same Excel-safe neutralization as CSV (SEC-16).
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from openpyxl import Workbook

from bfs_core.csvio.dialect import NUMERIC_COLUMNS, neutralize
from bfs_core.csvio.writer import write_csv
from bfs_core.model import DiagnosticReport, Statement

_DATE_COLUMNS = {
    "booking_date", "value_date", "opening_balance_date", "closing_balance_date",
}
_INT_COLUMNS = {
    "row_number", "statement_number", "sequence_number", "credit_count",
    "debit_count", "transaction_count",
}


def _cell_value(column: str, text: str, excel_safe: bool):
    if not text:
        return None
    if column in NUMERIC_COLUMNS:
        try:
            return Decimal(text)
        except InvalidOperation:
            return text
    if column in _INT_COLUMNS and text.isdigit():
        return int(text)
    if column in _DATE_COLUMNS:
        try:
            return date.fromisoformat(text)
        except ValueError:
            return text
    return neutralize(text, column, excel_safe)


def write_xlsx(statements: list[Statement], excel_safe: bool = True,
               created: "datetime | None" = None) -> tuple[bytes, DiagnosticReport]:
    # Reuse the CSV projection (single source of truth for the flat mapping),
    # in strict mode: neutralization for xlsx happens at cell level below.
    tx_bytes, st_bytes, report = write_csv(statements, excel_safe=False)
    workbook = Workbook()
    # Deterministic output: pin document timestamps to the injected clock.
    stamp = created or datetime(2000, 1, 1)
    workbook.properties.created = stamp
    workbook.properties.modified = stamp
    for title, payload in (("transactions", tx_bytes), ("statements", st_bytes)):
        sheet = workbook.active if title == "transactions" else workbook.create_sheet()
        sheet.title = title
        text = payload.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        header = rows[0]
        sheet.append(header)
        for row in rows[1:]:
            sheet.append([
                _cell_value(column, value, excel_safe)
                for column, value in zip(header, row, strict=False)
            ])
    out = io.BytesIO()
    workbook.save(out)
    return _pin_zip_timestamps(out.getvalue(), stamp), report


def _pin_zip_timestamps(payload: bytes, stamp: datetime) -> bytes:
    """xlsx is a zip; member mtimes default to wall-clock time. Rewrite every
    entry with the injected clock so output bytes are deterministic."""
    import zipfile

    fixed = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, 0)
    src = zipfile.ZipFile(io.BytesIO(payload))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            info = zipfile.ZipInfo(item.filename, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = item.external_attr
            content = src.read(item.filename)
            if item.filename == "docProps/core.xml":
                # openpyxl stamps dcterms:created/modified with wall-clock at
                # save time; pin both to the injected clock.
                import re
                iso = stamp.strftime("%Y-%m-%dT%H:%M:%SZ").encode()
                content = re.sub(rb"(<dcterms:(created|modified)[^>]*>)[^<]*(</dcterms:\2>)",
                                 rb"\g<1>" + iso + rb"\g<3>", content)
            dst.writestr(info, content)
    return out.getvalue()
