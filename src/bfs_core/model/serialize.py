"""Canonical JSON-compatible serialization of the normalized model.

Used for golden `normalized.json` artefacts: deterministic key order, Decimals as
strings, dates as ISO strings. Also provides the inverse for golden comparison.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bfs_core.model.statement import (
    Balance,
    BankTransactionCode,
    Counterparty,
    CreditDebit,
    EntryStatus,
    Statement,
    Transaction,
    TransactionsSummary,
)


def _summary(s: TransactionsSummary | None) -> dict[str, Any] | None:
    if s is None:
        return None
    return {
        "total_count": s.total_count,
        "total_sum": _opt_dec(s.total_sum),
        "credit_count": s.credit_count,
        "credit_sum": _opt_dec(s.credit_sum),
        "debit_count": s.debit_count,
        "debit_sum": _opt_dec(s.debit_sum),
        "net_amount": _opt_dec(s.net_amount),
        "net_credit_debit": s.net_credit_debit.value if s.net_credit_debit else None,
    }


def _summary_from(d: dict[str, Any] | None) -> TransactionsSummary | None:
    if d is None:
        return None
    return TransactionsSummary(
        total_count=d.get("total_count"),
        total_sum=Decimal(d["total_sum"]) if d.get("total_sum") else None,
        credit_count=d.get("credit_count"),
        credit_sum=Decimal(d["credit_sum"]) if d.get("credit_sum") else None,
        debit_count=d.get("debit_count"),
        debit_sum=Decimal(d["debit_sum"]) if d.get("debit_sum") else None,
        net_amount=Decimal(d["net_amount"]) if d.get("net_amount") else None,
        net_credit_debit=CreditDebit(d["net_credit_debit"]) if d.get("net_credit_debit") else None,
    )


def _balance(b: Balance | None) -> dict[str, str] | None:
    if b is None:
        return None
    return {
        "credit_debit": b.credit_debit.value,
        "date": b.date.isoformat(),
        "currency": b.currency,
        "amount": str(b.amount),
    }


def _counterparty(c: Counterparty | None) -> dict[str, Any] | None:
    if c is None:
        return None
    return {"name": c.name, "account": c.account, "bic": c.bic, "is_agent": c.is_agent}


def _btc(b: BankTransactionCode | None) -> dict[str, Any] | None:
    if b is None:
        return None
    return {
        "domain": b.domain, "family": b.family, "sub_family": b.sub_family,
        "proprietary": b.proprietary, "proprietary_issuer": b.proprietary_issuer,
    }


def _opt_dec(d: Decimal | None) -> str | None:
    return None if d is None else str(d)


def transaction_to_dict(t: Transaction) -> dict[str, Any]:
    return {
        "value_date": t.value_date.isoformat(),
        "booking_date": t.booking_date.isoformat() if t.booking_date else None,
        "credit_debit": t.credit_debit.value,
        "is_reversal": t.is_reversal,
        "amount": str(t.amount),
        "currency": t.currency,
        "funds_code": t.funds_code,
        "swift_tx_type": t.swift_tx_type,
        "btc": _btc(t.btc),
        "customer_reference": t.customer_reference,
        "bank_reference": t.bank_reference,
        "end_to_end_id": t.end_to_end_id,
        "mandate_id": t.mandate_id,
        "supplementary_details": t.supplementary_details,
        "counterparty": _counterparty(t.counterparty),
        "remittance_unstructured": list(t.remittance_unstructured),
        "creditor_reference": t.creditor_reference,
        "purpose_code": t.purpose_code,
        "return_reason": t.return_reason,
        "charges_amount": _opt_dec(t.charges_amount),
        "instructed_amount": _opt_dec(t.instructed_amount),
        "instructed_currency": t.instructed_currency,
        "exchange_rate": _opt_dec(t.exchange_rate),
        "entry_reference": t.entry_reference,
        "status": t.status.value,
        "additional_info": t.additional_info,
        "details": [transaction_to_dict(d) for d in t.details],
    }


def statement_to_dict(s: Statement) -> dict[str, Any]:
    return {
        "statement_id": s.statement_id,
        "account_iban": s.account_iban,
        "account_other_id": s.account_other_id,
        "account_currency": s.account_currency,
        "related_reference": s.related_reference,
        "statement_number": s.statement_number,
        "sequence_number": s.sequence_number,
        "page_count": s.page_count,
        "electronic_seq_number": s.electronic_seq_number,
        "creation_datetime": s.creation_datetime.isoformat() if s.creation_datetime else None,
        "from_datetime": s.from_datetime.isoformat() if s.from_datetime else None,
        "to_datetime": s.to_datetime.isoformat() if s.to_datetime else None,
        "opening_balance": _balance(s.opening_balance),
        "closing_balance": _balance(s.closing_balance),
        "opening_is_intermediate": s.opening_is_intermediate,
        "closing_is_intermediate": s.closing_is_intermediate,
        "closing_available": _balance(s.closing_available),
        "forward_available": [_balance(b) for b in s.forward_available],
        "other_balances": [{"type": code, "balance": _balance(b)} for code, b in s.other_balances],
        "transactions": [transaction_to_dict(t) for t in s.transactions],
        "summary": _summary(s.summary),
        "additional_info": s.additional_info,
        "source_format": s.source_format,
    }


def _balance_from(d: dict[str, str] | None) -> Balance | None:
    if d is None:
        return None
    return Balance(
        credit_debit=CreditDebit(d["credit_debit"]),
        date=date.fromisoformat(d["date"]),
        currency=d["currency"],
        amount=Decimal(d["amount"]),
    )


def transaction_from_dict(d: dict[str, Any]) -> Transaction:
    return Transaction(
        value_date=date.fromisoformat(d["value_date"]),
        booking_date=date.fromisoformat(d["booking_date"]) if d.get("booking_date") else None,
        credit_debit=CreditDebit(d["credit_debit"]),
        is_reversal=bool(d.get("is_reversal", False)),
        amount=Decimal(d["amount"]),
        currency=d.get("currency"),
        funds_code=d.get("funds_code"),
        swift_tx_type=d.get("swift_tx_type"),
        btc=BankTransactionCode(**d["btc"]) if d.get("btc") else None,
        customer_reference=d.get("customer_reference"),
        bank_reference=d.get("bank_reference"),
        end_to_end_id=d.get("end_to_end_id"),
        mandate_id=d.get("mandate_id"),
        supplementary_details=d.get("supplementary_details"),
        counterparty=Counterparty(**d["counterparty"]) if d.get("counterparty") else None,
        remittance_unstructured=tuple(d.get("remittance_unstructured", ())),
        creditor_reference=d.get("creditor_reference"),
        purpose_code=d.get("purpose_code"),
        return_reason=d.get("return_reason"),
        charges_amount=Decimal(d["charges_amount"]) if d.get("charges_amount") else None,
        instructed_amount=Decimal(d["instructed_amount"]) if d.get("instructed_amount") else None,
        instructed_currency=d.get("instructed_currency"),
        exchange_rate=Decimal(d["exchange_rate"]) if d.get("exchange_rate") else None,
        entry_reference=d.get("entry_reference"),
        status=EntryStatus(d.get("status", "BOOK")),
        additional_info=d.get("additional_info"),
        details=tuple(transaction_from_dict(x) for x in d.get("details", ())),
    )


def statement_from_dict(d: dict[str, Any]) -> Statement:
    opening = _balance_from(d["opening_balance"])
    closing = _balance_from(d["closing_balance"])
    assert opening is not None and closing is not None
    return Statement(
        statement_id=d["statement_id"],
        account_iban=d.get("account_iban"),
        account_other_id=d.get("account_other_id"),
        account_currency=d["account_currency"],
        related_reference=d.get("related_reference"),
        statement_number=d.get("statement_number"),
        sequence_number=d.get("sequence_number"),
        page_count=d.get("page_count"),
        electronic_seq_number=d.get("electronic_seq_number"),
        creation_datetime=datetime.fromisoformat(d["creation_datetime"]) if d.get("creation_datetime") else None,
        from_datetime=datetime.fromisoformat(d["from_datetime"]) if d.get("from_datetime") else None,
        to_datetime=datetime.fromisoformat(d["to_datetime"]) if d.get("to_datetime") else None,
        opening_balance=opening,
        closing_balance=closing,
        opening_is_intermediate=bool(d.get("opening_is_intermediate", False)),
        closing_is_intermediate=bool(d.get("closing_is_intermediate", False)),
        closing_available=_balance_from(d.get("closing_available")),
        forward_available=tuple(
            b for b in (_balance_from(x) for x in d.get("forward_available", ())) if b
        ),
        other_balances=tuple(
            (x["type"], b) for x in d.get("other_balances", ())
            if (b := _balance_from(x["balance"])) is not None
        ),
        transactions=[transaction_from_dict(x) for x in d.get("transactions", ())],
        summary=_summary_from(d.get("summary")),
        additional_info=d.get("additional_info"),
        source_format=d.get("source_format", ""),
    )
