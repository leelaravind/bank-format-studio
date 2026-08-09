"""camt.053 writers (v02/v08): normalized Statements → schema-valid XML bytes.

Deterministic: element order fixed by schema sequences, timestamps come from the
injected `now` clock, no randomness. Every generated document is self-validated
against the bundled XSD before being returned — an invalid product of this writer
is a defect and raises E_INTERNAL.

Loss handling (DATA-MAPPING-RESEARCH.md): funds_code, supplementary_details and
merged-page structure have no camt slot; they are appended to AddtlNtryInf /
AddtlStmtInf and recorded as LossNotes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import lxml.etree as etree

from bfs_core.camt.validate import validate_bytes
from bfs_core.camt.versions import VersionSpec
from bfs_core.errors import E_INTERNAL, W_REFERENCE_TRUNCATED, BfsError
from bfs_core.model import (
    Balance,
    CreditDebit,
    DiagnosticReport,
    LossKind,
    Statement,
    Transaction,
)


def _fmt(amount: Decimal) -> str:
    return format(amount, "f")


def _el(parent: etree._Element, tag: str, text: str | None = None,
        **attrs: str) -> etree._Element:
    node = etree.SubElement(parent, tag, attrib=attrs)
    if text is not None:
        node.text = text
    return node


def _el_fit(parent: etree._Element, tag: str, value: str, max_len: int,
            report: DiagnosticReport, where: str, field: str,
            direction: str) -> etree._Element:
    """Schema-length-capped element. Truncation is never silent (C-3): the cut
    is diagnosed and recorded as an information loss."""
    if len(value) > max_len:
        report.warning(W_REFERENCE_TRUNCATED, value=value, where=where)
        report.loss(field, direction, LossKind.TRUNCATED,
                    f"{value!r} truncated to the schema maximum of {max_len} characters",
                    where)
        value = value[:max_len]
    return _el(parent, tag, value)


def _amt_el(parent: etree._Element, tag: str, amount: Decimal, currency: str) -> None:
    _el(parent, tag, _fmt(amount), Ccy=currency)


def _bal_el(parent: etree._Element, code: str, balance: Balance) -> None:
    bal = _el(parent, "Bal")
    tp = _el(bal, "Tp")
    cdop = _el(tp, "CdOrPrtry")
    _el(cdop, "Cd", code)
    _amt_el(bal, "Amt", balance.amount, balance.currency)
    _el(bal, "CdtDbtInd", "CRDT" if balance.credit_debit is CreditDebit.CREDIT else "DBIT")
    dt = _el(bal, "Dt")
    _el(dt, "Dt", balance.date.isoformat())


def _btc_el(parent: etree._Element, t: Transaction, direction: str,
            report: DiagnosticReport, where: str) -> None:
    """BkTxCd is mandatory in Ntry. Preference: structured btc → mapped from SWIFT
    code → proprietary carry of the SWIFT code → PMNT/MCRD/OTHR fallback."""
    from bfs_core.convert.btc_map import swift_to_btc  # deferred: avoids import cycle

    node = _el(parent, "BkTxCd")
    btc = t.btc
    if btc is not None and btc.domain and btc.family:
        domn = _el(node, "Domn")
        _el(domn, "Cd", btc.domain)
        fmly = _el(domn, "Fmly")
        _el(fmly, "Cd", btc.family)
        _el(fmly, "SubFmlyCd", btc.sub_family or "OTHR")
        return
    mapped = swift_to_btc(t.swift_tx_type)
    if mapped is not None:
        domn = _el(node, "Domn")
        _el(domn, "Cd", mapped.domain)
        fmly = _el(domn, "Fmly")
        _el(fmly, "Cd", mapped.family)
        _el(fmly, "SubFmlyCd", mapped.sub_family or "OTHR")
    prtry_code = None
    if btc is not None and btc.proprietary:
        prtry_code = btc.proprietary
        issuer = btc.proprietary_issuer
    elif t.swift_tx_type:
        prtry_code = t.swift_tx_type
        issuer = "SWIFT-MT940"
    else:
        issuer = None
    if prtry_code:
        prtry = _el(node, "Prtry")
        _el(prtry, "Cd", prtry_code)
        if issuer:
            _el(prtry, "Issr", issuer)
    elif mapped is None:
        # No information at all: fallback with a loss note, never silent.
        domn = _el(node, "Domn")
        _el(domn, "Cd", "PMNT")
        fmly = _el(domn, "Fmly")
        _el(fmly, "Cd", "MCRD")
        _el(fmly, "SubFmlyCd", "OTHR")
        report.loss("transaction type", direction, LossKind.DERIVED,
                    "no bank transaction code available; defaulted to PMNT/MCRD/OTHR", where)


def _party_els(txdtls: etree._Element, t: Transaction, spec: VersionSpec,
               report: DiagnosticReport, where: str, direction: str) -> None:
    cp = t.counterparty
    if cp is None or cp.is_empty():
        return
    parties = _el(txdtls, "RltdPties")
    role = "Dbtr" if t.credit_debit is CreditDebit.CREDIT else "Cdtr"
    if cp.name:
        holder = _el(parties, role)
        if spec.party_wrapped:
            target = _el(holder, "Pty")
        else:
            target = holder
        _el_fit(target, "Nm", cp.name, 140, report, where, "counterparty name", direction)
    if cp.account:
        acct = _el(parties, f"{role}Acct")
        acct_id = _el(acct, "Id")
        if cp.account[:2].isalpha() and cp.account[2:4].isdigit():
            _el(acct_id, "IBAN", cp.account)
        else:
            othr = _el(acct_id, "Othr")
            _el(othr, "Id", cp.account)
    if cp.bic:
        agents = _el(txdtls, "RltdAgts")
        agt = _el(agents, f"{role}Agt")
        fin = _el(agt, "FinInstnId")
        _el(fin, spec.bic_tag, cp.bic)


def _txdtls_el(ntry: etree._Element, t: Transaction, spec: VersionSpec,
               currency: str, report: DiagnosticReport, direction: str,
               where: str) -> None:
    detail_list = t.details if t.details else (
        (t,) if (t.end_to_end_id or t.mandate_id or t.counterparty
                 or t.remittance_unstructured or t.creditor_reference
                 or t.purpose_code or t.return_reason or t.instructed_amount
                 or t.customer_reference) else ())
    if not detail_list:
        return
    is_batch = len(detail_list) > 1
    # C-1: camt.02 AmtDtls/TxAmt has no per-detail CdtDbtInd. For MIXED-direction
    # batches, writing bare amounts would corrupt detail signs on reread — so the
    # per-detail amounts are omitted entirely and the loss is diagnosed.
    mixed = is_batch and len({d.credit_debit for d in detail_list}) > 1
    write_v02_amounts = is_batch and spec.key == "02" and not mixed
    if is_batch and spec.key == "02" and mixed:
        report.loss("batch detail amounts/directions", direction, LossKind.DROPPED,
                    "camt.053.001.02 cannot carry per-detail debit/credit direction; "
                    "mixed-direction batch detail amounts omitted to prevent sign "
                    "corruption (references and remittance are preserved)", where)
    ntrydtls = _el(ntry, "NtryDtls")
    for d in detail_list:
        txdtls = _el(ntrydtls, "TxDtls")
        refs = _el(txdtls, "Refs")
        if d.bank_reference and d is not t:
            _el_fit(refs, "AcctSvcrRef", d.bank_reference, 35, report, where,
                    "bank_reference", direction)
        if d.customer_reference and d.customer_reference != d.end_to_end_id:
            _el_fit(refs, "InstrId", d.customer_reference, 35, report, where,
                    "customer_reference", direction)
        _el_fit(refs, "EndToEndId", d.end_to_end_id or d.customer_reference or "NOTPROVIDED",
                35, report, where, "end_to_end_id", direction)
        if d.mandate_id:
            _el_fit(refs, "MndtId", d.mandate_id, 35, report, where, "mandate_id", direction)
        # GATE-2: .08 TxDtls carries Amt/CdtDbtInd directly.
        if is_batch and spec.key != "02":
            _amt_el(txdtls, "Amt", d.amount, d.currency or currency)
            _el(txdtls, "CdtDbtInd",
                "CRDT" if d.credit_debit is CreditDebit.CREDIT else "DBIT")
        if write_v02_amounts or d.instructed_amount is not None:
            amtdtls = _el(txdtls, "AmtDtls")
            if d.instructed_amount is not None:
                instd = _el(amtdtls, "InstdAmt")
                _amt_el(instd, "Amt", d.instructed_amount, d.instructed_currency or currency)
                if d.exchange_rate is not None:
                    xchg = _el(instd, "CcyXchg")
                    _el(xchg, "SrcCcy", d.instructed_currency or currency)
                    _el(xchg, "XchgRate", _fmt(d.exchange_rate))
            if write_v02_amounts:
                txamt = _el(amtdtls, "TxAmt")
                _amt_el(txamt, "Amt", d.amount, d.currency or currency)
        _party_els(txdtls, d, spec, report, where, direction)
        if d.purpose_code:
            purp = _el(txdtls, "Purp")
            _el_fit(purp, "Cd", d.purpose_code, 4, report, where, "purpose_code", direction)
        if d.remittance_unstructured or d.creditor_reference:
            rmt = _el(txdtls, "RmtInf")
            for line in d.remittance_unstructured:
                for i in range(0, len(line), 140):
                    _el(rmt, "Ustrd", line[i:i + 140])
            if d.creditor_reference:
                strd = _el(rmt, "Strd")
                cref = _el(strd, "CdtrRefInf")
                _el_fit(cref, "Ref", d.creditor_reference, 35, report, where,
                        "creditor_reference", direction)
        if d.return_reason:
            rtr = _el(txdtls, "RtrInf")
            rsn = _el(rtr, "Rsn")
            _el_fit(rsn, "Cd", d.return_reason, 4, report, where, "return_reason", direction)


def _ntry_el(stmt_el: etree._Element, t: Transaction, spec: VersionSpec, currency: str,
             report: DiagnosticReport, direction: str, where: str) -> None:
    ntry = _el(stmt_el, "Ntry")
    if t.entry_reference:
        _el_fit(ntry, "NtryRef", t.entry_reference, 35, report, where,
                "entry_reference", direction)
    _amt_el(ntry, "Amt", t.amount, t.currency or currency)
    _el(ntry, "CdtDbtInd", "CRDT" if t.credit_debit is CreditDebit.CREDIT else "DBIT")
    if t.is_reversal:
        _el(ntry, "RvslInd", "true")
    if spec.status_is_choice:
        sts = _el(ntry, "Sts")
        _el(sts, "Cd", t.status.value)
    else:
        _el(ntry, "Sts", t.status.value)
    if t.booking_date:
        bookg = _el(ntry, "BookgDt")
        _el(bookg, "Dt", t.booking_date.isoformat())
    val = _el(ntry, "ValDt")
    _el(val, "Dt", t.value_date.isoformat())
    if t.bank_reference:
        _el_fit(ntry, "AcctSvcrRef", t.bank_reference, 35, report, where,
                "bank_reference", direction)
    _btc_el(ntry, t, direction, report, where)
    if t.charges_amount is not None:
        # GATE-2 structural difference: .02 ChargesInformation6 mandates Amt;
        # .08 Charges6 uses TtlChrgsAndTaxAmt.
        chrgs = _el(ntry, "Chrgs")
        if spec.key == "02":
            _amt_el(chrgs, "Amt", t.charges_amount, t.currency or currency)
        else:
            _amt_el(chrgs, "TtlChrgsAndTaxAmt", t.charges_amount, t.currency or currency)

    _txdtls_el(ntry, t, spec, currency, report, direction, where)

    additional_bits: list[str] = []
    if t.additional_info:
        additional_bits.append(t.additional_info)
    if t.funds_code:
        additional_bits.append(f"MT940 funds code: {t.funds_code}")
        report.loss("funds_code", direction, LossKind.FLATTENED,
                    "no camt slot; preserved in AddtlNtryInf", where)
    if t.supplementary_details:
        additional_bits.append(f"MT940 supplementary details: {t.supplementary_details}")
        report.loss("supplementary_details", direction, LossKind.FLATTENED,
                    "no camt slot; preserved in AddtlNtryInf", where)
    if additional_bits:
        _el_fit(ntry, "AddtlNtryInf", " | ".join(additional_bits), 500,
                report, where, "additional entry info", direction)


def write_camt053(statements: list[Statement], spec: VersionSpec,
                  now: datetime) -> tuple[bytes, DiagnosticReport]:
    """Serialize statements as one camt.053 document of the given version.
    `now` is the injected clock for GrpHdr/CreDtTm (determinism requirement)."""
    report = DiagnosticReport()
    direction = f"model->camt.053.001.{spec.key}"
    nsmap = {None: spec.namespace}
    root = etree.Element("Document", nsmap=nsmap)
    doc = etree.SubElement(root, "BkToCstmrStmt")
    grp = etree.SubElement(doc, "GrpHdr")
    first_id = statements[0].statement_id if statements else "STMT"
    _el(grp, "MsgId", f"BFS-{first_id}"[:35])
    _el(grp, "CreDtTm", now.replace(microsecond=0).isoformat())

    for s in statements:
        where = f"statement {s.statement_id!r}"
        stmt_el = _el(doc, "Stmt")
        _el_fit(stmt_el, "Id", s.statement_id, 35, report, where, "statement_id", direction)
        if spec.has_pagination:
            # GATE-3: .08 pagination carries the MT940 :28C: page number.
            pgntn = _el(stmt_el, "StmtPgntn")
            _el(pgntn, "PgNb", str(s.sequence_number if s.sequence_number is not None else 1))
            _el(pgntn, "LastPgInd", "true")
        eseq = s.electronic_seq_number or s.statement_number
        if eseq is not None:
            _el(stmt_el, "ElctrncSeqNb", str(eseq))
        if s.statement_number is not None:
            _el(stmt_el, "LglSeqNb", str(s.statement_number))
        _el(stmt_el, "CreDtTm",
            (s.creation_datetime or now).replace(microsecond=0).isoformat())
        if s.from_datetime and s.to_datetime:
            frto = _el(stmt_el, "FrToDt")
            _el(frto, "FrDtTm", s.from_datetime.isoformat())
            _el(frto, "ToDtTm", s.to_datetime.isoformat())
        acct = _el(stmt_el, "Acct")
        acct_id = _el(acct, "Id")
        if s.account_iban:
            _el(acct_id, "IBAN", s.account_iban)
        else:
            othr = _el(acct_id, "Othr")
            _el_fit(othr, "Id", s.account_other_id or s.account_raw or "UNKNOWN",
                    34, report, where, "account id", direction)
        _el(acct, "Ccy", s.account_currency)

        _bal_el(stmt_el, "OPBD", s.opening_balance)
        _bal_el(stmt_el, "CLBD", s.closing_balance)
        if s.closing_available:
            _bal_el(stmt_el, "CLAV", s.closing_available)
        for fwd in s.forward_available:
            _bal_el(stmt_el, "FWAV", fwd)
        for code, balance in s.other_balances:
            _bal_el(stmt_el, code if len(code) == 4 else "INFO", balance)

        if s.summary is not None:
            sm = s.summary
            summry = _el(stmt_el, "TxsSummry")
            ttl = _el(summry, "TtlNtries")
            if sm.total_count is not None:
                _el(ttl, "NbOfNtries", str(sm.total_count))
            if sm.total_sum is not None:
                _el(ttl, "Sum", _fmt(sm.total_sum))
            if sm.net_amount is not None and sm.net_credit_debit is not None:
                if spec.key == "02":
                    _el(ttl, "TtlNetNtryAmt", _fmt(sm.net_amount))
                    _el(ttl, "CdtDbtInd",
                        "CRDT" if sm.net_credit_debit is CreditDebit.CREDIT else "DBIT")
                else:
                    net = _el(ttl, "TtlNetNtry")
                    _el(net, "Amt", _fmt(sm.net_amount))
                    _el(net, "CdtDbtInd",
                        "CRDT" if sm.net_credit_debit is CreditDebit.CREDIT else "DBIT")
            if sm.credit_count is not None or sm.credit_sum is not None:
                cdt = _el(summry, "TtlCdtNtries")
                if sm.credit_count is not None:
                    _el(cdt, "NbOfNtries", str(sm.credit_count))
                if sm.credit_sum is not None:
                    _el(cdt, "Sum", _fmt(sm.credit_sum))
            if sm.debit_count is not None or sm.debit_sum is not None:
                dbt = _el(summry, "TtlDbtNtries")
                if sm.debit_count is not None:
                    _el(dbt, "NbOfNtries", str(sm.debit_count))
                if sm.debit_sum is not None:
                    _el(dbt, "Sum", _fmt(sm.debit_sum))

        for i, t in enumerate(s.transactions, 1):
            _ntry_el(stmt_el, t, spec, s.account_currency, report,
                     direction, f"{where}, entry {i}")

        additional_bits = []
        if s.additional_info:
            additional_bits.append(s.additional_info)
        if s.related_reference:
            additional_bits.append(f"MT940 related reference (:21:): {s.related_reference}")
            report.loss("related_reference", direction, LossKind.FLATTENED,
                        "no camt slot; preserved in AddtlStmtInf", where)
        if s.page_count and s.page_count > 1:
            additional_bits.append(f"merged from {s.page_count} MT940 pages")
            report.loss("statement pages", direction, LossKind.MERGED,
                        f"{s.page_count} MT940 pages merged into one camt statement", where)
        if s.sequence_number is not None and not spec.has_pagination:
            report.loss("sequence_number", direction, LossKind.DROPPED,
                        "camt.053.001.02 has no pagination element (GATE-3)", where)
        if additional_bits:
            _el_fit(stmt_el, "AddtlStmtInf", " | ".join(additional_bits), 500,
                    report, where, "additional statement info", direction)

    payload = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                             pretty_print=True)
    check = DiagnosticReport()
    if not validate_bytes(payload, spec, check):
        first = check.errors[0].message if check.errors else "unknown"
        raise BfsError(E_INTERNAL,
                       detail=f"generated camt.053.001.{spec.key} failed self-validation: {first}")
    return payload, report
