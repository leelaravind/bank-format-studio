"""camt.053 reader: bytes → normalized Statements + diagnostics.

Hardened parse (DTD rejected, no network, bounded tree) → version detection →
XSD validation against bundled schema → version-adapted mapping (GATE-2).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import lxml.etree as etree

from bfs_core.camt.validate import validate_bytes
from bfs_core.camt.versions import V02_BALANCE_CODES, VersionSpec, detect_version
from bfs_core.errors import (
    E_CAMT_SCHEMA_INVALID,
    E_XML_DTD_FORBIDDEN,
    E_XML_NOT_WELL_FORMED,
    W_BATCH_SUM_MISMATCH,
    W_NON_BOOKED_ENTRY,
    W_UNKNOWN_BALANCE_TYPE,
    BfsError,
)
from bfs_core.model import (
    Balance,
    BankTransactionCode,
    Counterparty,
    CreditDebit,
    DiagnosticReport,
    EntryStatus,
    LossKind,
    Statement,
    Transaction,
    TransactionsSummary,
    validate_currency,
)
from bfs_core.security import DEFAULT_LIMITS, Limits


def _hardened_parse(data: bytes, limits: Limits) -> etree._Element:
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(data, parser)
    except etree.XMLSyntaxError as exc:
        message = str(exc)
        if "ENTITY" in message.upper() or "DOCTYPE" in message.upper():
            raise BfsError(E_XML_DTD_FORBIDDEN) from exc
        raise BfsError(E_XML_NOT_WELL_FORMED, detail=message) from exc
    doc = root.getroottree()
    if doc.docinfo.internalDTD is not None or doc.docinfo.externalDTD is not None:
        raise BfsError(E_XML_DTD_FORBIDDEN)
    return root


def _ns(spec: VersionSpec) -> dict[str, str]:
    return {"c": spec.namespace}


def _text(node: etree._Element | None, path: str, ns: dict[str, str]) -> str | None:
    if node is None:
        return None
    found = node.findtext(path, namespaces=ns)
    return found.strip() if found and found.strip() else None


def _find(node: etree._Element | None, path: str, ns: dict[str, str]) -> etree._Element | None:
    return None if node is None else node.find(path, ns)


def _date_of(node: etree._Element | None, ns: dict[str, str]) -> date | None:
    """DateAndDateTimeChoice: Dt or DtTm."""
    if node is None:
        return None
    dt = _text(node, "c:Dt", ns)
    if dt:
        return date.fromisoformat(dt)
    dttm = _text(node, "c:DtTm", ns)
    if dttm:
        return datetime.fromisoformat(dttm).date()
    return None


def _datetime_of(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def _amount_of(node: etree._Element | None) -> tuple[Decimal, str] | None:
    if node is None or node.text is None:
        return None
    return Decimal(node.text.strip()), validate_currency(node.get("Ccy", ""), where="Amt/@Ccy")


def _cd_of(text: str | None) -> CreditDebit:
    return CreditDebit.CREDIT if text == "CRDT" else CreditDebit.DEBIT


def _balance_of(bal: etree._Element, ns: dict[str, str], where: str) -> tuple[str, Balance]:
    code = _text(bal, "c:Tp/c:CdOrPrtry/c:Cd", ns) or _text(bal, "c:Tp/c:CdOrPrtry/c:Prtry", ns) or "?"
    amt = _amount_of(_find(bal, "c:Amt", ns))
    assert amt is not None  # Amt is schema-mandatory
    day = _date_of(_find(bal, "c:Dt", ns), ns)
    assert day is not None  # Dt is schema-mandatory
    return code, Balance(
        credit_debit=_cd_of(_text(bal, "c:CdtDbtInd", ns)),
        date=day,
        currency=amt[1],
        amount=amt[0],
    )


def _party_of(pty_el: etree._Element | None, acct_el: etree._Element | None,
              agt_el: etree._Element | None, spec: VersionSpec,
              ns: dict[str, str]) -> Counterparty | None:
    name = None
    is_agent = False
    if pty_el is not None:
        if spec.party_wrapped:
            inner = _find(pty_el, "c:Pty", ns)
            if inner is not None:
                name = _text(inner, "c:Nm", ns)
            else:
                agt = _find(pty_el, "c:Agt", ns)
                if agt is not None:
                    name = _text(agt, "c:FinInstnId/c:Nm", ns)
                    is_agent = True
        else:
            name = _text(pty_el, "c:Nm", ns)
    account = None
    if acct_el is not None:
        account = _text(acct_el, "c:Id/c:IBAN", ns) or _text(acct_el, "c:Id/c:Othr/c:Id", ns)
    bic = None
    if agt_el is not None:
        bic = _text(agt_el, f"c:FinInstnId/c:{spec.bic_tag}", ns)
    if name or account or bic:
        return Counterparty(name=name, account=account, bic=bic, is_agent=is_agent)
    return None


def _btc_of(node: etree._Element | None, ns: dict[str, str]) -> BankTransactionCode | None:
    if node is None:
        return None
    domain = _text(node, "c:Domn/c:Cd", ns)
    family = _text(node, "c:Domn/c:Fmly/c:Cd", ns)
    sub = _text(node, "c:Domn/c:Fmly/c:SubFmlyCd", ns)
    prtry = _text(node, "c:Prtry/c:Cd", ns)
    issuer = _text(node, "c:Prtry/c:Issr", ns)
    if domain or family or sub or prtry:
        return BankTransactionCode(domain=domain, family=family, sub_family=sub,
                                   proprietary=prtry, proprietary_issuer=issuer)
    return None


def _status_of(ntry: etree._Element, spec: VersionSpec, ns: dict[str, str]) -> str:
    if spec.status_is_choice:
        return _text(ntry, "c:Sts/c:Cd", ns) or _text(ntry, "c:Sts/c:Prtry", ns) or "BOOK"
    return _text(ntry, "c:Sts", ns) or "BOOK"


def _tx_details(txdtls: etree._Element, entry_cd: CreditDebit, value_date: date,
                booking_date: date | None, spec: VersionSpec,
                ns: dict[str, str]) -> Transaction:
    refs = _find(txdtls, "c:Refs", ns)
    # .08 has TxDtls/Amt directly; .02 batch details carry AmtDtls/TxAmt/Amt (GATE-2).
    amt = _amount_of(_find(txdtls, "c:Amt", ns)) or \
        _amount_of(_find(txdtls, "c:AmtDtls/c:TxAmt/c:Amt", ns))
    cd_text = _text(txdtls, "c:CdtDbtInd", ns)
    cd = _cd_of(cd_text) if cd_text else entry_cd

    parties = _find(txdtls, "c:RltdPties", ns)
    agents = _find(txdtls, "c:RltdAgts", ns)
    # Counterparty: debtor side for credits, creditor side for debits.
    if cd is CreditDebit.CREDIT:
        pty = _find(parties, "c:Dbtr", ns)
        acct = _find(parties, "c:DbtrAcct", ns)
        agt = _find(agents, "c:DbtrAgt", ns)
    else:
        pty = _find(parties, "c:Cdtr", ns)
        acct = _find(parties, "c:CdtrAcct", ns)
        agt = _find(agents, "c:CdtrAgt", ns)

    rmt = _find(txdtls, "c:RmtInf", ns)
    ustrd = tuple(
        el.text.strip() for el in (rmt.findall("c:Ustrd", ns) if rmt is not None else [])
        if el.text and el.text.strip()
    )
    instd = _amount_of(_find(txdtls, "c:AmtDtls/c:InstdAmt/c:Amt", ns))
    rate_text = _text(txdtls, "c:AmtDtls/c:InstdAmt/c:CcyXchg/c:XchgRate", ns) or \
        _text(txdtls, "c:AmtDtls/c:TxAmt/c:CcyXchg/c:XchgRate", ns)
    charges = _text(txdtls, "c:Chrgs/c:TtlChrgsAndTaxAmt", ns) or \
        _text(txdtls, "c:Chrgs/c:Rcrd/c:Amt", ns) or _text(txdtls, "c:Chrgs/c:Amt", ns)

    return Transaction(
        value_date=value_date,
        booking_date=booking_date,
        credit_debit=cd,
        amount=amt[0] if amt else Decimal(0),
        currency=amt[1] if amt else None,
        end_to_end_id=_text(refs, "c:EndToEndId", ns),
        mandate_id=_text(refs, "c:MndtId", ns),
        customer_reference=_text(refs, "c:EndToEndId", ns) or _text(refs, "c:InstrId", ns),
        bank_reference=_text(refs, "c:AcctSvcrRef", ns),
        counterparty=_party_of(pty, acct, agt, spec, ns),
        remittance_unstructured=ustrd,
        creditor_reference=_text(rmt, "c:Strd/c:CdtrRefInf/c:Ref", ns),
        purpose_code=_text(txdtls, "c:Purp/c:Cd", ns),
        return_reason=_text(txdtls, "c:RtrInf/c:Rsn/c:Cd", ns),
        instructed_amount=instd[0] if instd else None,
        instructed_currency=instd[1] if instd else None,
        exchange_rate=Decimal(rate_text) if rate_text else None,
        charges_amount=Decimal(charges) if charges else None,
        additional_info=_text(txdtls, "c:AddtlTxInf", ns),
    )


def _entry_of(ntry: etree._Element, account_currency: str, spec: VersionSpec,
              ns: dict[str, str], report: DiagnosticReport, where: str) -> Transaction:
    amt = _amount_of(_find(ntry, "c:Amt", ns))
    assert amt is not None  # schema-mandatory
    cd = _cd_of(_text(ntry, "c:CdtDbtInd", ns))
    value_date = _date_of(_find(ntry, "c:ValDt", ns), ns)
    booking_date = _date_of(_find(ntry, "c:BookgDt", ns), ns)
    status_text = _status_of(ntry, spec, ns)
    try:
        status = EntryStatus(status_text)
    except ValueError:
        status = EntryStatus.INFO
        report.warning(W_NON_BOOKED_ENTRY, value=status_text, where=where)
    if status is not EntryStatus.BOOK:
        report.warning(W_NON_BOOKED_ENTRY, value=status_text, where=where)

    txdtls_list = ntry.findall("c:NtryDtls/c:TxDtls", ns)
    details: tuple[Transaction, ...] = ()
    base: Transaction | None = None
    effective_value = value_date or booking_date or date(1970, 1, 1)
    if len(txdtls_list) == 1:
        base = _tx_details(txdtls_list[0], cd, effective_value, booking_date, spec, ns)
    elif len(txdtls_list) > 1:
        details = tuple(
            _tx_details(t, cd, effective_value, booking_date, spec, ns) for t in txdtls_list
        )
        detail_sum = sum((t.signed() for t in details), Decimal(0))
        entry_signed = amt[0] * cd.sign
        if all(t.amount for t in details) and detail_sum != entry_signed:
            report.warning(W_BATCH_SUM_MISMATCH, where=where,
                           detail=f"entry {entry_signed} vs details sum {detail_sum}")

    entry_charges = _text(ntry, "c:Chrgs/c:TtlChrgsAndTaxAmt", ns) or \
        _text(ntry, "c:Chrgs/c:Amt", ns) or _text(ntry, "c:Chrgs/c:Rcrd/c:Amt", ns)
    entry = Transaction(
        value_date=effective_value,
        booking_date=booking_date,
        credit_debit=cd,
        charges_amount=Decimal(entry_charges) if entry_charges else None,
        is_reversal=(_text(ntry, "c:RvslInd", ns) == "true"),
        amount=amt[0],
        currency=None if amt[1] == account_currency else amt[1],
        btc=_btc_of(_find(ntry, "c:BkTxCd", ns), ns) or (base.btc if base else None),
        bank_reference=_text(ntry, "c:AcctSvcrRef", ns) or (base.bank_reference if base else None),
        entry_reference=_text(ntry, "c:NtryRef", ns),
        status=status,
        additional_info=_text(ntry, "c:AddtlNtryInf", ns),
        details=details,
    )
    if base is not None:
        entry.end_to_end_id = base.end_to_end_id
        entry.mandate_id = base.mandate_id
        entry.customer_reference = base.customer_reference
        entry.counterparty = base.counterparty
        entry.remittance_unstructured = base.remittance_unstructured
        entry.creditor_reference = base.creditor_reference
        entry.purpose_code = base.purpose_code
        entry.return_reason = base.return_reason
        entry.instructed_amount = base.instructed_amount
        entry.instructed_currency = base.instructed_currency
        entry.exchange_rate = base.exchange_rate
        entry.charges_amount = base.charges_amount or entry.charges_amount
        if base.additional_info:
            entry.additional_info = (
                f"{entry.additional_info} | {base.additional_info}"
                if entry.additional_info else base.additional_info)
    return entry


def _summary_of(stmt: etree._Element, ns: dict[str, str]) -> TransactionsSummary | None:
    node = _find(stmt, "c:TxsSummry", ns)
    if node is None:
        return None

    def _int(path: str) -> int | None:
        t = _text(node, path, ns)
        return int(t) if t else None

    def _dec(path: str) -> Decimal | None:
        t = _text(node, path, ns)
        return Decimal(t) if t else None

    # .02: TtlNetNtryAmt + CdtDbtInd; .08: TtlNetNtry/Amt + TtlNetNtry/CdtDbtInd (GATE-2)
    net = _dec("c:TtlNtries/c:TtlNetNtryAmt") or _dec("c:TtlNtries/c:TtlNetNtry/c:Amt")
    net_cd_text = _text(node, "c:TtlNtries/c:CdtDbtInd", ns) or \
        _text(node, "c:TtlNtries/c:TtlNetNtry/c:CdtDbtInd", ns)
    return TransactionsSummary(
        total_count=_int("c:TtlNtries/c:NbOfNtries"),
        total_sum=_dec("c:TtlNtries/c:Sum"),
        credit_count=_int("c:TtlCdtNtries/c:NbOfNtries"),
        credit_sum=_dec("c:TtlCdtNtries/c:Sum"),
        debit_count=_int("c:TtlDbtNtries/c:NbOfNtries"),
        debit_sum=_dec("c:TtlDbtNtries/c:Sum"),
        net_amount=net,
        net_credit_debit=_cd_of(net_cd_text) if net_cd_text else None,
    )


def _map_statement(stmt: etree._Element, spec: VersionSpec, ns: dict[str, str],
                   creation: datetime | None, report: DiagnosticReport,
                   index: int) -> Statement:
    where = f"statement {index + 1}"
    acct = _find(stmt, "c:Acct", ns)
    iban = _text(acct, "c:Id/c:IBAN", ns)
    other = _text(acct, "c:Id/c:Othr/c:Id", ns)
    acct_ccy = _text(acct, "c:Ccy", ns)

    opening = closing = closing_avail = None
    forward: list[Balance] = []
    others: list[tuple[str, Balance]] = []
    for bal in stmt.findall("c:Bal", ns):
        code, balance = _balance_of(bal, ns, where)
        if code == "OPBD" and opening is None:
            opening = balance
        elif code == "CLBD" and closing is None:
            closing = balance
        elif code == "CLAV" and closing_avail is None:
            closing_avail = balance
        elif code == "FWAV":
            forward.append(balance)
        else:
            if spec.balance_codes_closed and code not in V02_BALANCE_CODES:
                report.warning(W_UNKNOWN_BALANCE_TYPE, value=code, where=where)
            elif not spec.balance_codes_closed and (len(code) > 4 or not code.isalnum()):
                report.warning(W_UNKNOWN_BALANCE_TYPE, value=code, where=where)
            others.append((code, balance))

    # E5: PRCD (previous closing) substitutes a missing OPBD.
    if opening is None:
        prcd = next((b for c, b in others if c == "PRCD"), None)
        if prcd is not None:
            opening = prcd
            report.info(W_UNKNOWN_BALANCE_TYPE, value="PRCD",
                        where=f"{where}: used as opening balance (no OPBD present)")
    if opening is None or closing is None:
        raise BfsError(E_CAMT_SCHEMA_INVALID, version=f"camt.053.001.{spec.key}",
                       detail="statement lacks OPBD/PRCD opening or CLBD closing balance",
                       where=where)

    currency = acct_ccy or opening.currency
    entries = stmt.findall("c:Ntry", ns)
    transactions = [
        _entry_of(entry, currency, spec, ns, report, f"{where}, entry {i + 1}")
        for i, entry in enumerate(entries)
    ]

    def _int_of(path: str) -> int | None:
        t = _text(stmt, path, ns)
        return int(t) if t and t.isdigit() else None

    # Read-side fidelity: elements we deliberately do not map are recorded as loss,
    # never silently ignored (FIDELITY rule).
    for tag in ("Intrst", "RltdAcct", "RptgSrc", "CpyDplctInd"):
        if _find(stmt, f"c:{tag}", ns) is not None:
            report.loss(tag, f"camt.053.001.{spec.key}->model", LossKind.DROPPED,
                        f"optional element {tag} is not carried by the normalized model", where)
    for i, entry in enumerate(entries, 1):
        for tag in ("Avlbty", "ComssnWvrInd", "TechInptChanl", "Intrst", "CorpActn"):
            if _find(entry, f"c:{tag}", ns) is not None:
                report.loss(tag, f"camt.053.001.{spec.key}->model", LossKind.DROPPED,
                            f"optional element {tag} is not carried by the normalized model",
                            f"{where}, entry {i}")

    frto = _find(stmt, "c:FrToDt", ns)
    return Statement(
        statement_id=_text(stmt, "c:Id", ns) or f"UNNAMED-{index + 1}",
        account_iban=iban,
        account_other_id=other,
        account_raw=iban or other,
        account_currency=validate_currency(currency, where=f"{where} account"),
        statement_number=_int_of("c:LglSeqNb"),
        electronic_seq_number=_int_of("c:ElctrncSeqNb"),
        sequence_number=_int_of("c:StmtPgntn/c:PgNb") if spec.has_pagination else None,
        creation_datetime=_datetime_of(_text(stmt, "c:CreDtTm", ns)) or creation,
        from_datetime=_datetime_of(_text(frto, "c:FrDtTm", ns)),
        to_datetime=_datetime_of(_text(frto, "c:ToDtTm", ns)),
        opening_balance=opening,
        closing_balance=closing,
        closing_available=closing_avail,
        forward_available=tuple(forward),
        other_balances=tuple(others),
        transactions=transactions,
        summary=_summary_of(stmt, ns),
        additional_info=_text(stmt, "c:AddtlStmtInf", ns),
        source_format=f"camt.053.001.{spec.key}",
    )


def read_camt053(data: bytes, limits: Limits = DEFAULT_LIMITS,
                 validate: bool = True) -> tuple[list[Statement], DiagnosticReport]:
    """Parse camt.053 bytes into normalized statements.

    Raises BfsError for non-camt/unsupported-version/malformed/DTD inputs.
    Schema violations are ERROR diagnostics in the report; mapping is not attempted
    on schema-invalid documents.
    """
    report = DiagnosticReport()
    limits.check_size(len(data))
    root = _hardened_parse(data, limits)
    namespace = root.tag.split("}")[0].strip("{") if root.tag.startswith("{") else ""
    spec = detect_version(namespace)
    if validate and not validate_bytes(data, spec, report):
        return [], report
    ns = _ns(spec)
    doc = _find(root, "c:BkToCstmrStmt", ns)
    creation = _datetime_of(_text(doc, "c:GrpHdr/c:CreDtTm", ns))
    statements = [
        _map_statement(stmt, spec, ns, creation, report, i)
        for i, stmt in enumerate(doc.findall("c:Stmt", ns))
    ]
    total = sum(len(s.transactions) for s in statements)
    limits.check_count(total)
    return statements, report
