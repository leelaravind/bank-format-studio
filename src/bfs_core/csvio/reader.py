"""CSV import: (transactions.csv, statements.csv) → Statements.

Import accepts ONLY the product's own documented dialect (locked V1 guardrail).
statements.csv is authoritative for balances; derived per-row balance columns are
cross-checked, not trusted. Nothing is ever evaluated (SEC-17).
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from bfs_core.csvio.dialect import (
    STATEMENTS_REQUIRED,
    TRANSACTIONS_REQUIRED,
    deneutralize,
)
from bfs_core.errors import (
    E_CSV_BAD_VALUE,
    E_CSV_INCONSISTENT,
    E_CSV_MISSING_COLUMN,
    BfsError,
)
from bfs_core.model import (
    Balance,
    BankTransactionCode,
    Counterparty,
    CreditDebit,
    DiagnosticReport,
    EntryStatus,
    Statement,
    Transaction,
    validate_currency,
)
from bfs_core.security import DEFAULT_LIMITS, Limits


def _decode(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode("utf-8")


def _rows(data: bytes, required: list[str], which: str,
          limits: Limits) -> list[dict[str, str]]:
    limits.check_size(len(data), which)
    reader = csv.DictReader(io.StringIO(_decode(data)))
    header = reader.fieldnames or []
    for column in required:
        if column not in header:
            raise BfsError(E_CSV_MISSING_COLUMN, value=column, where=which)
    out = []
    for i, row in enumerate(reader, 2):
        out.append({k: deneutralize(v) if isinstance(v, str) else "" for k, v in row.items()})
        limits.check_count(i, f"{which} rows")
    return out


def _dec(row: dict[str, str], column: str, where: str) -> Decimal | None:
    raw = (row.get(column) or "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise BfsError(E_CSV_BAD_VALUE, value=raw, column=column, where=where,
                       detail="not a decimal number") from exc


def _date(row: dict[str, str], column: str, where: str) -> date | None:
    raw = (row.get(column) or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise BfsError(E_CSV_BAD_VALUE, value=raw, column=column, where=where,
                       detail="expected YYYY-MM-DD") from exc


def _get(row: dict[str, str], column: str) -> str | None:
    value = (row.get(column) or "").strip()
    return value or None


def _tx_from_row(row: dict[str, str], where: str, statement_currency: str) -> Transaction:
    amount = _dec(row, "amount", where)
    if amount is None:
        raise BfsError(E_CSV_BAD_VALUE, value="", column="amount", where=where,
                       detail="amount is required")
    cd_text = _get(row, "credit_debit")
    if cd_text not in ("C", "D"):
        raise BfsError(E_CSV_BAD_VALUE, value=cd_text or "", column="credit_debit",
                       where=where, detail="expected C or D")
    cd = CreditDebit(cd_text)
    if (amount < 0) != (cd is CreditDebit.DEBIT) and amount != 0:
        raise BfsError(E_CSV_INCONSISTENT, where=where,
                       detail=f"amount {amount} sign contradicts credit_debit {cd.value}")
    value_date = _date(row, "value_date", where)
    if value_date is None:
        raise BfsError(E_CSV_BAD_VALUE, value="", column="value_date", where=where,
                       detail="value_date is required")
    status_text = _get(row, "status") or "BOOK"
    try:
        status = EntryStatus(status_text)
    except ValueError as exc:
        raise BfsError(E_CSV_BAD_VALUE, value=status_text, column="status",
                       where=where, detail="expected BOOK, PDNG or INFO") from exc
    row_currency = _get(row, "currency")
    btc = None
    if _get(row, "btc_domain") or _get(row, "btc_family"):
        btc = BankTransactionCode(domain=_get(row, "btc_domain"),
                                  family=_get(row, "btc_family"),
                                  sub_family=_get(row, "btc_subfamily"))
    cp = None
    if _get(row, "counterparty_name") or _get(row, "counterparty_account") or _get(row, "counterparty_bic"):
        cp = Counterparty(name=_get(row, "counterparty_name"),
                          account=_get(row, "counterparty_account"),
                          bic=_get(row, "counterparty_bic"))
    remittance = _get(row, "remittance_info")
    return Transaction(
        value_date=value_date,
        booking_date=_date(row, "booking_date", where),
        credit_debit=cd,
        is_reversal=(_get(row, "reversal") == "true"),
        amount=abs(amount),
        currency=None if not row_currency or row_currency == statement_currency else row_currency,
        swift_tx_type=_get(row, "transaction_type_code"),
        btc=btc,
        customer_reference=_get(row, "customer_reference"),
        bank_reference=_get(row, "bank_reference"),
        end_to_end_id=_get(row, "end_to_end_id"),
        mandate_id=_get(row, "mandate_id"),
        supplementary_details=_get(row, "supplementary_details"),
        counterparty=cp,
        remittance_unstructured=(remittance,) if remittance else (),
        creditor_reference=_get(row, "creditor_reference"),
        purpose_code=_get(row, "purpose_code"),
        return_reason=None,
        funds_code=_get(row, "funds_code"),
        instructed_amount=_dec(row, "instructed_amount", where),
        instructed_currency=_get(row, "instructed_currency"),
        exchange_rate=_dec(row, "exchange_rate", where),
        charges_amount=_dec(row, "charges_amount", where),
        entry_reference=_get(row, "entry_reference"),
        status=status,
        additional_info=_get(row, "additional_info"),
    )


def _occurrence_key(row: dict[str, str], sid: str, ordinal_counts: dict[str, int],
                    where: str) -> tuple[str, int]:
    """B-2: statement identity is (statement_id, statement_occurrence). When the
    column is absent (dialect v1.0 files) the ordinal of appearance substitutes —
    unambiguous only while statement_ids are unique, which is validated by the caller."""
    occ_text = _get(row, "statement_occurrence")
    if occ_text is not None:
        if not occ_text.isdigit() or int(occ_text) < 1:
            raise BfsError(E_CSV_BAD_VALUE, value=occ_text, column="statement_occurrence",
                           where=where, detail="expected a positive integer")
        return sid, int(occ_text)
    ordinal_counts[sid] = ordinal_counts.get(sid, 0) + 1
    return sid, ordinal_counts[sid]


def read_csv(transactions_csv: bytes, statements_csv: bytes,
             limits: Limits = DEFAULT_LIMITS) -> tuple[list[Statement], DiagnosticReport]:
    report = DiagnosticReport()
    st_rows = _rows(statements_csv, STATEMENTS_REQUIRED, "statements.csv", limits)
    tx_rows = _rows(transactions_csv, TRANSACTIONS_REQUIRED, "transactions.csv", limits)
    if not st_rows:
        raise BfsError(E_CSV_INCONSISTENT, where="statements.csv", detail="no statement rows")

    statements: dict[tuple[str, int], Statement] = {}
    order: list[tuple[str, int]] = []
    st_ordinals: dict[str, int] = {}
    has_occurrence_column = any("statement_occurrence" in row for row in st_rows[:1])
    for i, row in enumerate(st_rows, 2):
        where = f"statements.csv row {i}"
        sid = _get(row, "statement_id")
        if not sid:
            raise BfsError(E_CSV_BAD_VALUE, value="", column="statement_id", where=where,
                           detail="statement_id is required")
        key = _occurrence_key(row, sid, st_ordinals, where)
        if key in statements:
            raise BfsError(E_CSV_INCONSISTENT, where=where,
                           detail=f"duplicate statement identity {key[0]!r} occurrence {key[1]}")
        currency = validate_currency(_get(row, "currency") or "", where=where)
        ob = _dec(row, "opening_balance", where)
        cb = _dec(row, "closing_balance", where)
        ob_date = _date(row, "opening_balance_date", where)
        cb_date = _date(row, "closing_balance_date", where)
        if ob is None or cb is None or ob_date is None or cb_date is None:
            raise BfsError(E_CSV_BAD_VALUE, value="", column="opening/closing balance",
                           where=where, detail="balances and their dates are required")
        cav = _dec(row, "closing_available_balance", where)
        number_text = _get(row, "statement_number")
        seq_text = _get(row, "sequence_number")
        statements[key] = Statement(
            statement_id=sid,
            account_iban=_get(row, "account_iban"),
            account_other_id=_get(row, "account_other_id"),
            account_currency=currency,
            statement_number=int(number_text) if number_text else None,
            sequence_number=int(seq_text) if seq_text else None,
            opening_balance=Balance.from_signed(ob, ob_date, currency),
            closing_balance=Balance.from_signed(cb, cb_date, currency),
            closing_available=Balance.from_signed(cav, cb_date, currency) if cav is not None else None,
            source_format="csv",
        )
        order.append(key)

    # Ambiguity guard: duplicate statement_ids without an occurrence column can
    # not be mapped to transaction rows deterministically.
    id_counts: dict[str, int] = {}
    for key in order:
        id_counts[key[0]] = id_counts.get(key[0], 0) + 1
    duplicated_ids = {sid for sid, n in id_counts.items() if n > 1}
    if duplicated_ids and not has_occurrence_column:
        raise BfsError(
            E_CSV_INCONSISTENT, where="statements.csv",
            detail=f"statement_id(s) {sorted(duplicated_ids)} appear more than once but the "
                   "file has no statement_occurrence column (dialect v1.1) to distinguish them")

    tx_ordinals: dict[str, int] = {}
    for i, row in enumerate(tx_rows, 2):
        where = f"transactions.csv row {i}"
        sid = _get(row, "statement_id")
        if not sid:
            raise BfsError(E_CSV_INCONSISTENT, where=where,
                           detail="transaction row lacks a statement_id")
        occ_text = _get(row, "statement_occurrence")
        if occ_text is not None:
            key = _occurrence_key(row, sid, tx_ordinals, where)
        elif sid in duplicated_ids:
            raise BfsError(E_CSV_INCONSISTENT, where=where,
                           detail=f"statement_id {sid!r} is duplicated but this transaction "
                                  "row has no statement_occurrence value")
        else:
            key = (sid, 1)
        if key not in statements:
            raise BfsError(E_CSV_INCONSISTENT, where=where,
                           detail=f"statement identity {key[0]!r} occurrence {key[1]} "
                                  "has no row in statements.csv")
        s = statements[key]
        s.transactions.append(_tx_from_row(row, where, s.account_currency))

    for s in statements.values():
        s.transactions = _regroup_batches(s.transactions)

    return [statements[key] for key in order], report


def _regroup_batches(transactions: list[Transaction]) -> list[Transaction]:
    """Rows sharing a non-empty entry_reference are the exploded TxDtls of one
    batch entry (CSV-FORMAT-STRATEGY §5); regroup them so the Ntry-level entry —
    the reconciliation-authoritative unit — is reconstructed."""
    out: list[Transaction] = []
    i = 0
    while i < len(transactions):
        t = transactions[i]
        j = i + 1
        while (t.entry_reference and j < len(transactions)
               and transactions[j].entry_reference == t.entry_reference):
            j += 1
        group = transactions[i:j]
        if len(group) == 1:
            out.append(t)
        else:
            net = sum((d.signed() for d in group), Decimal(0))
            cd = CreditDebit.CREDIT if net >= 0 else CreditDebit.DEBIT
            out.append(Transaction(
                value_date=t.value_date,
                booking_date=t.booking_date,
                credit_debit=cd,
                amount=abs(net),
                is_reversal=t.is_reversal,
                currency=t.currency,
                swift_tx_type=t.swift_tx_type,
                entry_reference=t.entry_reference,
                status=t.status,
                details=tuple(group),
            ))
        i = j
    return out
