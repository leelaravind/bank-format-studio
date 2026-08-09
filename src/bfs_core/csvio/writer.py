"""CSV export: Statements → (transactions.csv bytes, statements.csv bytes).

Reconciliation figures in statements.csv are computed by the reconciliation
engine — declared balances are written as declared, never repaired.
"""

from __future__ import annotations

import csv
import io

from bfs_core.csvio.dialect import (
    STATEMENTS_COLUMNS,
    TRANSACTIONS_COLUMNS,
    neutralize,
)
from bfs_core.model import (
    DiagnosticReport,
    LossKind,
    Statement,
    Transaction,
)
from bfs_core.reconcile import reconcile_statement

_DIRECTION = "model->csv"


def _writer(buffer: io.StringIO) -> csv.writer:
    return csv.writer(buffer, delimiter=",", quotechar='"',
                      quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")


def _encode(buffer: io.StringIO) -> bytes:
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


def _tx_rows(s: Statement, t: Transaction, report: DiagnosticReport,
             where: str) -> list[dict[str, str]]:
    """One row per movement; batch entries explode to one row per TxDtls (documented lossy)."""
    if t.details:
        report.loss("batch entry structure", _DIRECTION, LossKind.FLATTENED,
                    f"{len(t.details)} TxDtls exported as individual rows sharing "
                    f"entry_reference; Ntry-level aggregate reconstructable by grouping", where)
        rows = []
        for d in t.details:
            row = _tx_row(s, d)
            row["entry_reference"] = t.entry_reference or f"BATCH-{where.rsplit(' ', 1)[-1]}"
            row["transaction_type_code"] = row["transaction_type_code"] or (
                t.swift_tx_type or "")
            rows.append(row)
        return rows
    return [_tx_row(s, t)]


def _tx_row(s: Statement, t: Transaction) -> dict[str, str]:
    signed = t.signed()
    return {
        "statement_id": s.statement_id,
        "account_iban": s.account_iban or "",
        "account_other_id": s.account_other_id or "",
        "statement_number": "" if s.statement_number is None else str(s.statement_number),
        "sequence_number": "" if s.sequence_number is None else str(s.sequence_number),
        "currency": t.currency or s.account_currency,
        "booking_date": t.booking_date.isoformat() if t.booking_date else "",
        "value_date": t.value_date.isoformat(),
        "amount": str(signed),
        "credit_debit": t.credit_debit.value,
        "reversal": "true" if t.is_reversal else "false",
        "transaction_type_code": t.swift_tx_type or (t.btc.proprietary if t.btc and t.btc.proprietary else ""),
        "customer_reference": t.customer_reference or "",
        "bank_reference": t.bank_reference or "",
        "remittance_info": " ".join(t.remittance_unstructured),
        "end_to_end_id": t.end_to_end_id or "",
        "mandate_id": t.mandate_id or "",
        "purpose_code": t.purpose_code or "",
        "creditor_reference": t.creditor_reference or "",
        "counterparty_name": t.counterparty.name if t.counterparty and t.counterparty.name else "",
        "counterparty_account": t.counterparty.account if t.counterparty and t.counterparty.account else "",
        "counterparty_bic": t.counterparty.bic if t.counterparty and t.counterparty.bic else "",
        "btc_domain": t.btc.domain if t.btc and t.btc.domain else "",
        "btc_family": t.btc.family if t.btc and t.btc.family else "",
        "btc_subfamily": t.btc.sub_family if t.btc and t.btc.sub_family else "",
        "funds_code": t.funds_code or "",
        "supplementary_details": t.supplementary_details or "",
        "entry_reference": t.entry_reference or "",
        "instructed_amount": "" if t.instructed_amount is None else str(t.instructed_amount),
        "instructed_currency": t.instructed_currency or "",
        "exchange_rate": "" if t.exchange_rate is None else str(t.exchange_rate),
        "charges_amount": "" if t.charges_amount is None else str(t.charges_amount),
        "status": t.status.value,
        "additional_info": t.additional_info or "",
    }


def write_csv(statements: list[Statement],
              excel_safe: bool = True) -> tuple[bytes, bytes, DiagnosticReport]:
    """Returns (transactions_csv, statements_csv, report). statements.csv is
    mandatory on every export (locked decision)."""
    report = DiagnosticReport()
    tx_buf = io.StringIO()
    tw = _writer(tx_buf)
    tw.writerow(TRANSACTIONS_COLUMNS)
    row_number = 0
    for s in statements:
        where = f"statement {s.statement_id!r}"
        for i, t in enumerate(s.transactions, 1):
            if len(t.remittance_unstructured) > 1:
                report.loss("remittance line structure", _DIRECTION, LossKind.FLATTENED,
                            "multiple remittance lines joined with spaces",
                            f"{where}, entry {i}")
            for row in _tx_rows(s, t, report, f"{where}, entry {i}"):
                row_number += 1
                row["row_number"] = str(row_number)
                row["statement_opening_balance"] = str(s.opening_balance.signed())
                row["statement_closing_balance"] = str(s.closing_balance.signed())
                tw.writerow([neutralize(row.get(c, ""), c, excel_safe)
                             for c in TRANSACTIONS_COLUMNS])

    st_buf = io.StringIO()
    sw = _writer(st_buf)
    sw.writerow(STATEMENTS_COLUMNS)
    for s in statements:
        recon = reconcile_statement(s)
        loss_flags = sorted({n.kind.value for n in report.loss_notes}) if report.loss_notes else []
        row = {
            "statement_id": s.statement_id,
            "account_iban": s.account_iban or "",
            "account_other_id": s.account_other_id or "",
            "statement_number": "" if s.statement_number is None else str(s.statement_number),
            "sequence_number": "" if s.sequence_number is None else str(s.sequence_number),
            "currency": s.account_currency,
            "opening_balance_date": s.opening_balance.date.isoformat(),
            "opening_balance": str(s.opening_balance.signed()),
            "closing_balance_date": s.closing_balance.date.isoformat(),
            "closing_balance": str(s.closing_balance.signed()),
            "closing_available_balance": str(s.closing_available.signed()) if s.closing_available else "",
            "total_credits": str(recon.total_credits),
            "total_debits": str(recon.total_debits),
            "credit_count": str(recon.credit_count),
            "debit_count": str(recon.debit_count),
            "transaction_count": str(recon.transaction_count),
            "source_format": s.source_format,
            "information_loss_flags": ";".join(loss_flags),
        }
        sw.writerow([neutralize(row.get(c, ""), c, excel_safe) for c in STATEMENTS_COLUMNS])
        for code, _b in s.other_balances:
            report.loss(f"balance {code}", _DIRECTION, LossKind.DROPPED,
                        f"balance type {code} has no CSV column", f"statement {s.statement_id!r}")
        for _f in s.forward_available:
            report.loss("forward available balance", _DIRECTION, LossKind.DROPPED,
                        "FWAV balances have no CSV column", f"statement {s.statement_id!r}")
        if s.summary is not None:
            report.loss("transactions summary", _DIRECTION, LossKind.DROPPED,
                        "declared TxsSummry figures are not exported (computed totals "
                        "are in statements.csv instead)", f"statement {s.statement_id!r}")

    return _encode(tx_buf), _encode(st_buf), report
