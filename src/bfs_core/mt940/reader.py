"""MT940 reader: bytes → normalized Statements + diagnostics.

Pipeline: decode (SEC-18) → strip envelopes/preambles → split into statement page
chunks → GATE-1 pre-scan → parse each chunk with the approved `mt940` library
(BSD-3-Clause), retrying with its ASNB variant tag → map to the normalized model
via :86: profiles → merge :60M:/:62M: page chains (INV-4).

Every heuristic (encoding fallback, entry-date year, page merge) emits a diagnostic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import mt940 as mt940lib
from mt940.tags import StatementASNB

from bfs_core.errors import (
    E_MT940_BAD_DC_MARK,
    E_MT940_MISSING_CLOSING,
    E_MT940_MISSING_OPENING,
    E_MT940_PARSE,
    E_PAGE_CHAIN_BROKEN,
    W_DANGLING_INTERMEDIATE,
    W_ENCODING_FALLBACK,
    W_ENTRY_DATE_YEAR_GUESSED,
    W_UNKNOWN_TAG,
    BfsError,
)
from bfs_core.model import (
    Balance,
    CreditDebit,
    DiagnosticReport,
    Statement,
    Transaction,
    validate_currency,
)
from bfs_core.mt940.profiles import parse_86
from bfs_core.security import DEFAULT_LIMITS, Limits

_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
_TAG_LINE_RE = re.compile(r"^:(\d{2}[A-Z]?|NS):", re.MULTILINE)
_KNOWN_TAGS = {"20", "21", "25", "28", "28C", "60F", "60M", "61", "86", "62F", "62M", "64", "65"}
# GATE-1 pre-scan: value date + optional entry date, then the D/C mark.
_61_PREFIX_RE = re.compile(r"^(\d{6})(\d{4}|\s{4})?\s?([A-Z]{1,2})")
_VALID_MARKS = {"C", "D", "RC", "RD"}
# A mark char followed by a digit/comma means the mark was 1 char and next is amount;
# handled by taking the longest valid candidate.


def _decode(data: bytes, report: DiagnosticReport) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        text = data.decode("cp1252", errors="replace")
        report.warning(W_ENCODING_FALLBACK, value="cp1252",
                       detail=f"first undecodable byte at offset {exc.start}")
        return text


def _strip_envelopes(text: str, report: DiagnosticReport) -> str:
    """Extract {4:...-} block contents when SWIFT FIN blocks are present;
    otherwise drop known proprietary preamble lines before the first :20:."""
    if "{4:" in text:
        blocks = re.findall(r"\{4:\s*(.*?)\r?\n-\s*\}", text, re.DOTALL)
        if blocks:
            return "\n".join(blocks)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(":20:"):
            if i > 0:
                dropped = [ln for ln in lines[:i] if ln.strip() and ln.strip() != ":940:"]
                if dropped:
                    report.info(W_UNKNOWN_TAG, value="preamble",
                                where="file header",
                                detail=f"{len(dropped)} non-tag header line(s) ignored")
            return "\n".join(lines[i:])
    return text


def _split_statements(text: str) -> list[str]:
    """Split on '-' separator lines, then on every ':20:' start."""
    chunks: list[str] = []
    for block in re.split(r"\r?\n-\s*(?:\r?\n|$)", text):
        if not block.strip():
            continue
        starts = [m.start() for m in re.finditer(r"^:20:", block, re.MULTILINE)]
        if len(starts) <= 1:
            chunks.append(block)
        else:
            for i, s in enumerate(starts):
                end = starts[i + 1] if i + 1 < len(starts) else len(block)
                chunks.append(block[s:end])
    return [c.strip("\r\n") for c in chunks if c.strip()]


def _prescan_gate1(chunk: str, where: str) -> None:
    """GATE-1: reject :61: lines whose D/C mark is not C/D/RC/RD before library parse."""
    for m in re.finditer(r"^:61:(.*)$", chunk, re.MULTILINE):
        body = m.group(1)
        pm = _61_PREFIX_RE.match(body)
        if not pm:
            continue  # left for the library parser to reject with full context
        candidate = pm.group(3)
        # candidate is 1-2 uppercase letters right after the dates. Valid forms:
        # 'C','D' (2nd letter may be a funds code), 'RC','RD'.
        if candidate in _VALID_MARKS:
            continue
        if candidate[0] in ("C", "D"):
            continue  # 1-char mark + funds code (e.g. 'CR' = C + funds R)
        raise BfsError(E_MT940_BAD_DC_MARK, value=candidate, where=where)


def _scan_unknown_tags(chunk: str, report: DiagnosticReport, where: str) -> list[str]:
    unknown_payload: list[str] = []
    seen: set[str] = set()
    for m in _TAG_LINE_RE.finditer(chunk):
        tag = m.group(1)
        if tag not in _KNOWN_TAGS and tag not in seen:
            seen.add(tag)
            report.warning(W_UNKNOWN_TAG, value=f":{tag}:", where=where)
    for m in re.finditer(r"^:NS:(.*)$", chunk, re.MULTILINE):
        unknown_payload.append(m.group(1).strip())
    return unknown_payload


def _processors() -> dict:
    """Library defaults minus the GVC :86: consumer — :86: interpretation is done by
    our profiles module so the verbatim text survives on Transaction.raw_86."""
    processors = dict(mt940lib.models.Transactions.DEFAULT_PROCESSORS)
    processors["post_transaction_details"] = []
    return processors


def _lib_parse(chunk: str, where: str) -> "mt940lib.models.Transactions":
    try:
        transactions = mt940lib.models.Transactions(processors=_processors())
        transactions.parse(chunk)
        return transactions
    except Exception:
        # Retry with the ASNB bank-variant statement tag (public fixture evidence).
        try:
            tag = StatementASNB()
            transactions = mt940lib.models.Transactions(
                tags={tag.id: tag}, processors=_processors())
            transactions.parse(chunk)
            return transactions
        except Exception as exc:
            raise BfsError(E_MT940_PARSE, where=where, detail=str(exc)) from exc


def _to_balance(lib_balance: object, kind: str, where: str) -> Balance:
    """Map an mt940 library Balance (signed amount, C/D status) to the model."""
    amount = lib_balance.amount.amount  # signed Decimal
    currency = validate_currency(lib_balance.amount.currency or "", where=f"{where} {kind}")
    day: date = lib_balance.date
    cd = CreditDebit.DEBIT if (lib_balance.status or "C").upper().startswith("D") else CreditDebit.CREDIT
    return Balance(credit_debit=cd, date=day, currency=currency, amount=abs(amount))


def _parse_account(raw: str) -> tuple[str | None, str | None, str | None]:
    """:25: content → (iban, other_id, currency_suffix)."""
    value = (raw or "").strip()
    suffix_ccy = None
    parts = value.split()
    if len(parts) == 2 and re.fullmatch(r"[A-Z]{3}", parts[1]):
        value, suffix_ccy = parts[0], parts[1]
    if _IBAN_RE.fullmatch(value):
        return value, None, suffix_ccy
    return None, value or None, suffix_ccy


@dataclass
class _Page:
    statement: Statement
    where: str


def _map_transaction(lib_tx: object, statement_currency: str,
                     report: DiagnosticReport, where: str) -> Transaction:
    d = lib_tx.data
    raw_status = (d.get("status") or "").upper()
    if raw_status not in _VALID_MARKS:
        raise BfsError(E_MT940_BAD_DC_MARK, value=raw_status, where=where)
    is_reversal = raw_status.startswith("R")
    mark = raw_status[-1]
    # GATE-1 mapping: RD = reversal of debit → credit-direction movement;
    # RC = reversal of credit → debit-direction movement.
    if is_reversal:
        cd = CreditDebit.CREDIT if mark == "D" else CreditDebit.DEBIT
    else:
        cd = CreditDebit.CREDIT if mark == "C" else CreditDebit.DEBIT

    amount_obj = d["amount"]
    amount = abs(amount_obj.amount)
    tx_currency = amount_obj.currency or None
    value_date = d["date"]
    entry_date = d.get("entry_date")
    if entry_date is not None and entry_date.year != value_date.year:
        report.warning(W_ENTRY_DATE_YEAR_GUESSED, value=entry_date.year,
                       where=f"{where}, value date {value_date.isoformat()}")

    raw_86 = d.get("transaction_details") or None
    parsed = parse_86(raw_86) if raw_86 else None

    additional_bits: list[str] = []
    if parsed:
        additional_bits.extend(parsed.additional)
    additional = " | ".join(additional_bits) or None

    remittance: tuple[str, ...] = ()
    if parsed:
        if parsed.style == "unstructured":
            remittance = tuple(parsed.remittance)
        else:
            remittance = tuple(parsed.remittance)

    return Transaction(
        value_date=value_date,
        booking_date=entry_date,
        credit_debit=cd,
        is_reversal=is_reversal,
        amount=amount,
        currency=None if (tx_currency is None or tx_currency == statement_currency) else tx_currency,
        funds_code=d.get("funds_code") or None,
        swift_tx_type=(d.get("id") or "").strip() or None,
        btc=parsed.btc if parsed else None,
        customer_reference=(d.get("customer_reference") or "").strip() or None,
        bank_reference=(d.get("bank_reference") or "").strip() or None,
        end_to_end_id=parsed.end_to_end_id if parsed else None,
        mandate_id=parsed.mandate_id if parsed else None,
        supplementary_details=(d.get("extra_details") or "").strip() or None,
        counterparty=parsed.counterparty if parsed else None,
        remittance_unstructured=remittance,
        creditor_reference=parsed.creditor_reference if parsed else None,
        purpose_code=parsed.purpose_code if parsed else None,
        return_reason=parsed.return_reason if parsed else None,
        additional_info=additional,
        raw_86=raw_86,
    )


def _map_chunk(chunk: str, index: int, report: DiagnosticReport, limits: Limits) -> _Page:
    where = f"statement {index + 1}"
    _prescan_gate1(chunk, where)
    ns_payload = _scan_unknown_tags(chunk, report, where)
    lib = _lib_parse(chunk, where)
    data = lib.data

    opening = data.get("final_opening_balance") or data.get("opening_balance")
    inter_opening = data.get("intermediate_opening_balance")
    closing = data.get("final_closing_balance") or data.get("closing_balance")
    inter_closing = data.get("intermediate_closing_balance")
    opening_is_intermediate = opening is None and inter_opening is not None
    closing_is_intermediate = closing is None and inter_closing is not None
    opening = opening or inter_opening
    closing = closing or inter_closing
    if opening is None:
        raise BfsError(E_MT940_MISSING_OPENING, where=where)
    if closing is None:
        raise BfsError(E_MT940_MISSING_CLOSING, where=where)

    opening_balance = _to_balance(opening, "opening balance", where)
    closing_balance = _to_balance(closing, "closing balance", where)
    currency = opening_balance.currency

    iban, other_id, suffix_ccy = _parse_account(data.get("account_identification") or "")
    if suffix_ccy:
        currency = validate_currency(suffix_ccy, where=f"{where} :25:")

    def _to_int(value: object) -> int | None:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    forward: list[Balance] = []
    fwd = data.get("forward_available_balance")
    if fwd is not None:
        forward.append(_to_balance(fwd, "forward available balance", where))
    available = data.get("available_balance")

    limits.check_count(len(lib))
    statement = Statement(
        statement_id=(data.get("transaction_reference") or "").strip() or f"UNNAMED-{index + 1}",
        related_reference=(data.get("related_reference") or "").strip() or None,
        account_iban=iban,
        account_other_id=other_id,
        account_raw=(data.get("account_identification") or "").strip() or None,
        account_currency=currency,
        statement_number=_to_int(data.get("statement_number")),
        sequence_number=_to_int(data.get("sequence_number")),
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        opening_is_intermediate=opening_is_intermediate,
        closing_is_intermediate=closing_is_intermediate,
        closing_available=_to_balance(available, "available balance", where) if available else None,
        forward_available=tuple(forward),
        transactions=[_map_transaction(t, currency, report, f"{where}, entry") for t in lib],
        additional_info=" | ".join(p for p in ns_payload if p) or None,
        source_format="mt940",
    )
    return _Page(statement=statement, where=where)


def _merge_pages(pages: list[_Page], report: DiagnosticReport) -> list[Statement]:
    merged: list[Statement] = []
    i = 0
    while i < len(pages):
        base = pages[i].statement
        page_count = 1
        while (
            i + 1 < len(pages)
            and base.closing_is_intermediate
            and pages[i + 1].statement.opening_is_intermediate
            and pages[i + 1].statement.statement_number == base.statement_number
        ):
            nxt = pages[i + 1].statement
            prev_close = base.closing_balance
            next_open = nxt.opening_balance
            if (prev_close.signed() != next_open.signed()
                    or prev_close.currency != next_open.currency):
                raise BfsError(
                    E_PAGE_CHAIN_BROKEN, page=page_count,
                    detail=f"{prev_close.signed()} {prev_close.currency} vs "
                           f"{next_open.signed()} {next_open.currency}")
            base.transactions.extend(nxt.transactions)
            base.closing_balance = nxt.closing_balance
            base.closing_is_intermediate = nxt.closing_is_intermediate
            base.closing_available = nxt.closing_available or base.closing_available
            base.forward_available = base.forward_available + nxt.forward_available
            base.sequence_number = nxt.sequence_number or base.sequence_number
            page_count += 1
            i += 1
        if page_count > 1:
            base.page_count = page_count
        if base.opening_is_intermediate or base.closing_is_intermediate:
            report.warning(W_DANGLING_INTERMEDIATE, where=pages[i].where)
        merged.append(base)
        i += 1
    return merged


def read_mt940(data: bytes, limits: Limits = DEFAULT_LIMITS) -> tuple[list[Statement], DiagnosticReport]:
    """Parse MT940 bytes into normalized statements. Raises BfsError on hard failures;
    returns per-statement warnings/notes in the DiagnosticReport."""
    report = DiagnosticReport()
    limits.check_size(len(data))
    text = _decode(data, report)
    for line_no, line in enumerate(text.splitlines(), 1):
        limits.check_line(len(line), f"line {line_no}")
    text = _strip_envelopes(text, report)
    chunks = _split_statements(text)
    if not chunks or not any(":20:" in c or ":61:" in c or ":60" in c for c in chunks):
        raise BfsError(E_MT940_PARSE, where="file", detail="no MT940 tags found")
    pages = [_map_chunk(chunk, i, report, limits) for i, chunk in enumerate(chunks)]
    statements = _merge_pages(pages, report)
    return statements, report
