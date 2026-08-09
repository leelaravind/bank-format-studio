"""MT940 writer: normalized Statements → bare-tag MT940 bytes (CRLF).

Output conventions (locked decisions):
- ONE documented :86: output style: SWIFT slash code words (GATE-4) —
  /EREF/ /PREF/ /MARF/ /ORDP|/BENM//NAME//IBAN|/ID//BIC/ /REMI/ /PURP//CD/ /RTRN/.
  German GVC is never written (input-side only).
- References longer than 16 chars are truncated in :61: subfields with the full
  value spilled into :86: and a W_REFERENCE_TRUNCATED warning + loss note.
- Text is transliterated to the SWIFT X character set (lossy, recorded).
- :86: content wraps at 65 characters; when content exceeds the nominal 6-line
  limit the writer keeps all lines (widely tolerated in practice) rather than
  losing data — recorded as a diagnostic-free documented behaviour.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from bfs_core.convert.btc_map import btc_to_swift
from bfs_core.errors import W_CHARSET_VIOLATION, W_REFERENCE_TRUNCATED
from bfs_core.model import (
    CreditDebit,
    DiagnosticReport,
    LossKind,
    Statement,
    Transaction,
    format_swift_amount,
)

_X_CHARSET_OK = re.compile(r"[A-Za-z0-9/\-?:().,'+ ]")
_DIRECTION = "model->mt940"


def _translit(text: str, report: DiagnosticReport, where: str,
              seen: set[str]) -> str:
    """SWIFT X charset transliteration: strip diacritics, replace the rest with '.'."""
    decomposed = unicodedata.normalize("NFKD", text)
    out: list[str] = []
    changed = False
    for ch in decomposed:
        if unicodedata.combining(ch):
            changed = True
            continue
        if _X_CHARSET_OK.match(ch):
            out.append(ch)
        else:
            out.append(".")
            changed = True
    if changed and where not in seen:
        seen.add(where)
        report.warning(W_CHARSET_VIOLATION, where=where)
        report.loss("text", _DIRECTION, LossKind.TRANSLITERATED,
                    "characters outside the SWIFT X set transliterated or replaced", where)
    return "".join(out)


def _yymmdd(d) -> str:
    return d.strftime("%y%m%d")


def _dc_mark(t: Transaction) -> str:
    # GATE-1 inverse mapping.
    if t.is_reversal:
        return "RD" if t.credit_debit is CreditDebit.CREDIT else "RC"
    return "C" if t.credit_debit is CreditDebit.CREDIT else "D"


def _balance_line(tag: str, balance) -> str:
    mark = "C" if balance.credit_debit is CreditDebit.CREDIT else "D"
    return f":{tag}:{mark}{_yymmdd(balance.date)}{balance.currency}{format_swift_amount(balance.amount)}"


def _ref16(value: str | None, default: str, report: DiagnosticReport, where: str,
           spill: list[str], label: str) -> str:
    if not value:
        return default
    if len(value) > 16:
        report.warning(W_REFERENCE_TRUNCATED, value=value, where=where)
        report.loss(label, _DIRECTION, LossKind.TRUNCATED,
                    f"{value!r} truncated to 16 chars in :61:; full value kept in :86:", where)
        spill.append(value)
        return value[:16]
    return value


def _tx_type(t: Transaction, report: DiagnosticReport, where: str) -> str:
    if t.swift_tx_type:
        code = t.swift_tx_type.upper()
        return code if len(code) == 4 else (code + "MSC")[:4]
    mapped = btc_to_swift(t.btc)
    if mapped:
        return mapped
    if t.btc is not None:
        report.loss("bank transaction code", _DIRECTION, LossKind.DERIVED,
                    f"BTC {t.btc.domain}/{t.btc.family}/{t.btc.sub_family or t.btc.proprietary} "
                    "has no SWIFT mapping; NMSC used", where)
    return "NMSC"


def _build_86(t: Transaction, report: DiagnosticReport, where: str,
              extra_refs: list[str]) -> str | None:
    parts: list[str] = []
    if t.end_to_end_id:
        parts.append(f"/EREF/{t.end_to_end_id}")
    elif extra_refs:
        parts.append(f"/EREF/{extra_refs[0]}")
    if t.creditor_reference:
        parts.append(f"/PREF/{t.creditor_reference}")
    if t.mandate_id:
        parts.append(f"/MARF/{t.mandate_id}")
    if t.return_reason:
        parts.append(f"/RTRN/{t.return_reason}")
    cp = t.counterparty
    if cp and not cp.is_empty():
        role = "ORDP" if t.credit_debit is CreditDebit.CREDIT else "BENM"
        section = f"/{role}/"
        if cp.name:
            section += f"/NAME/{cp.name}"
        if cp.account:
            section += f"/IBAN/{cp.account}" if (cp.account[:2].isalpha() and cp.account[2:4].isdigit()) \
                else f"/ID/{cp.account}"
        if cp.bic:
            section += f"/BIC/{cp.bic}"
        parts.append(section)
        if cp.is_agent:
            report.loss("counterparty agent flag", _DIRECTION, LossKind.FLATTENED,
                        "camt Party40Choice/Agt distinction not representable", where)
    if t.purpose_code:
        parts.append(f"/PURP//CD/{t.purpose_code}")
    if t.remittance_unstructured:
        joined = " ".join(t.remittance_unstructured)
        if len(t.remittance_unstructured) > 1:
            report.loss("remittance line structure", _DIRECTION, LossKind.FLATTENED,
                        f"{len(t.remittance_unstructured)} Ustrd lines joined into one /REMI/", where)
        parts.append(f"/REMI/{joined}")
    if t.charges_amount is not None:
        parts.append(f"/CHGS/{format_swift_amount(t.charges_amount)}")
    if t.instructed_amount is not None:
        ccy = t.instructed_currency or ""
        parts.append(f"/OCMT/{ccy}{format_swift_amount(t.instructed_amount)}")
    if t.additional_info:
        parts.append(t.additional_info if parts else t.additional_info)
    if t.details:
        report.loss("batch details", _DIRECTION, LossKind.FLATTENED,
                    f"{len(t.details)} camt TxDtls flattened into one :61: line", where)
    return "".join(parts) if parts else None


def _wrap_86(content: str) -> list[str]:
    lines = [content[i:i + 65] for i in range(0, len(content), 65)]
    return [":86:" + lines[0]] + lines[1:] if lines else []


def write_mt940(statements: list[Statement]) -> tuple[bytes, DiagnosticReport]:
    """Serialize statements as a bare-tag MT940 file (deterministic, CRLF)."""
    report = DiagnosticReport()
    seen_translit: set[str] = set()
    out: list[str] = []
    for s in statements:
        where = f"statement {s.statement_id!r}"
        sid = s.statement_id
        if len(sid) > 16:
            report.warning(W_REFERENCE_TRUNCATED, value=sid, where=where)
            report.loss("statement_id", _DIRECTION, LossKind.TRUNCATED,
                        f"{sid!r} truncated to 16 chars for :20:", where)
            sid = sid[:16]
        out.append(f":20:{_translit(sid, report, where + ' :20:', seen_translit)}")
        if s.related_reference:
            out.append(f":21:{s.related_reference[:16]}")
        account = s.account_iban or s.account_other_id or s.account_raw or "UNKNOWN"
        out.append(f":25:{_translit(account[:35], report, where + ' :25:', seen_translit)}")
        number = s.statement_number if s.statement_number is not None else 1
        seq = s.sequence_number
        out.append(f":28C:{number}" + (f"/{seq}" if seq is not None else ""))
        out.append(_balance_line("60F", s.opening_balance))
        for i, t in enumerate(s.transactions, 1):
            loc = f"{where}, entry {i}"
            spill: list[str] = []
            cust = _ref16(t.customer_reference or t.end_to_end_id, "NONREF",
                          report, loc, spill, "customer_reference")
            bank = _ref16(t.bank_reference, "", report, loc, spill, "bank_reference")
            line = (f":61:{_yymmdd(t.value_date)}"
                    + (t.booking_date.strftime("%m%d") if t.booking_date else "")
                    + _dc_mark(t)
                    + (t.funds_code or "")
                    + format_swift_amount(t.amount)
                    + _tx_type(t, report, loc)
                    + cust
                    + (f"//{bank}" if bank else ""))
            out.append(line)
            if t.supplementary_details:
                out.append(t.supplementary_details[:34])
            if t.currency is not None and t.currency != s.account_currency:
                report.loss("entry currency", _DIRECTION, LossKind.DROPPED,
                            f"per-entry currency {t.currency} not representable in MT940; "
                            "statement currency applies", loc)
            content = _build_86(t, report, loc, spill)
            if content:
                content = _translit(content, report, loc + " :86:", seen_translit)
                out.extend(_wrap_86(content))
        tag = "62M" if s.closing_is_intermediate else "62F"
        out.append(_balance_line(tag, s.closing_balance))
        if s.closing_available:
            out.append(_balance_line("64", s.closing_available))
        for fwd in s.forward_available:
            out.append(_balance_line("65", fwd))
        if s.summary is not None:
            report.loss("transactions summary", _DIRECTION, LossKind.DROPPED,
                        "camt TxsSummry has no MT940 representation", where)
        for code, _bal in s.other_balances:
            report.loss(f"balance {code}", _DIRECTION, LossKind.DROPPED,
                        f"balance type {code} has no MT940 tag", where)
        out.append("-")
    text = "\r\n".join(out) + "\r\n"
    return text.encode("ascii", errors="replace"), report
