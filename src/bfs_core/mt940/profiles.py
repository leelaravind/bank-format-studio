"""Bank-variant interpretation of MT940 field :86: content.

Three structural families (docs/FORMAT-NOTES.md §5):
  unstructured — free text → remittance lines
  nl_structured — slash code words (/EREF/, /BENM//NAME/, /REMI/, …)
  de_gvc — German DK: 3-digit GVC + ?nn subfields with SEPA code words (EREF+, SVWZ+, …)

Field :86: is only ever *interpreted*, never discarded: the verbatim text is kept
on Transaction.raw_86 and unrecognized content lands in additional_info.
German GVC is INPUT-SIDE ONLY (locked decision GATE-4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bfs_core.model import BankTransactionCode, Counterparty

_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
_BIC_RE = re.compile(r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")

# Slash code words we interpret (superset of the GATE-4 output vocabulary).
_NL_CODES = (
    "EREF", "PREF", "MARF", "CSID", "RTRN", "ACCW", "BENM", "ORDP", "CNTP",
    "NAME", "ID", "ADDR", "REMI", "ISDT", "PURP", "CD", "ULTB", "ULTD",
    "IBAN", "BIC", "TRTP", "OCMT", "EXCH", "CHGS", "SWOC",
)
_NL_SPLIT_RE = re.compile(r"/(" + "|".join(_NL_CODES) + r")/")
_GVC_RE = re.compile(r"^(\d{3})(\?.*)?$", re.DOTALL)
_GVC_FIELD_RE = re.compile(r"\?(\d{2})")
_SEPA_WORD_RE = re.compile(r"(EREF|KREF|MREF|CRED|DEBT|SVWZ|ABWA|ABWE|BIC|IBAN)\+")


@dataclass
class Parsed86:
    end_to_end_id: str | None = None
    mandate_id: str | None = None
    purpose_code: str | None = None
    return_reason: str | None = None
    creditor_reference: str | None = None
    counterparty: Counterparty | None = None
    remittance: list[str] = field(default_factory=list)
    btc: BankTransactionCode | None = None
    additional: list[str] = field(default_factory=list)
    style: str = "unstructured"


def detect_style(text: str) -> str:
    stripped = text.strip()
    if _GVC_RE.match(stripped) and "?" in stripped:
        return "de_gvc"
    if _NL_SPLIT_RE.search(stripped):
        return "nl_structured"
    return "unstructured"


def parse_86(text: str, style: str | None = None) -> Parsed86:
    style = style or detect_style(text)
    if style == "de_gvc":
        return _parse_gvc(text)
    if style == "nl_structured":
        return _parse_nl(text)
    result = Parsed86(style="unstructured")
    result.remittance = [line.strip() for line in text.splitlines() if line.strip()]
    return result


def _clean(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def _parse_nl(text: str) -> Parsed86:
    result = Parsed86(style="nl_structured")
    flat = " ".join(text.splitlines())
    parts = _NL_SPLIT_RE.split(flat)
    # parts = [prefix, CODE, value, CODE, value, ...]
    prefix = parts[0].strip().strip("/")
    if prefix:
        result.additional.append(_clean(prefix))
    pairs = list(zip(parts[1::2], parts[2::2]))
    cp_name = cp_account = cp_bic = None
    party_section: str | None = None
    for code, raw in pairs:
        value = _clean(raw).strip("/ ").strip()
        if not value and code not in ("BENM", "ORDP", "CNTP"):
            continue
        if code == "EREF":
            result.end_to_end_id = value
        elif code == "MARF":
            result.mandate_id = value
        elif code == "PREF":
            result.creditor_reference = value
        elif code == "CSID":
            result.additional.append(f"creditor scheme id: {value}")
        elif code == "RTRN":
            result.return_reason = value
        elif code in ("BENM", "ORDP", "CNTP", "ACCW", "ULTB", "ULTD"):
            party_section = code
            if value:
                # bare value directly after the party code word (e.g. /CNTP/IBAN BIC NAME/)
                tokens = value.split()
                for token in tokens:
                    if _IBAN_RE.match(token) and not cp_account:
                        cp_account = token
                    elif _BIC_RE.match(token) and not cp_bic:
                        cp_bic = token
                    else:
                        cp_name = f"{cp_name} {token}".strip() if cp_name else token
        elif code == "NAME":
            if party_section in ("ULTB", "ULTD"):
                result.additional.append(f"ultimate party: {value}")
            else:
                cp_name = value
        elif code == "IBAN":
            cp_account = value
        elif code == "BIC":
            cp_bic = value
        elif code == "ID":
            if party_section and not cp_account:
                cp_account = value
            else:
                result.additional.append(f"id: {value}")
        elif code == "ADDR":
            result.additional.append(f"address: {value}")
        elif code == "REMI":
            result.remittance.append(value)
        elif code == "PURP":
            party_section = "PURP"
        elif code == "CD":
            if party_section == "PURP":
                result.purpose_code = value
            else:
                result.additional.append(f"code: {value}")
        elif code == "ISDT":
            result.additional.append(f"settlement date: {value}")
        elif code in ("TRTP", "OCMT", "EXCH", "CHGS", "SWOC"):
            result.additional.append(f"{code.lower()}: {value}")
    if cp_name or cp_account or cp_bic:
        result.counterparty = Counterparty(name=cp_name, account=cp_account, bic=cp_bic)
    return result


def _parse_gvc(text: str) -> Parsed86:
    result = Parsed86(style="de_gvc")
    flat = "".join(text.splitlines())
    match = _GVC_RE.match(flat.strip())
    assert match is not None  # guarded by detect_style
    gvc = match.group(1)
    result.btc = BankTransactionCode(proprietary=gvc, proprietary_issuer="DK-GVC")
    rest = match.group(2) or ""
    # split into ?nn fields, preserving order
    fields: list[tuple[str, str]] = []
    positions = [(m.start(), m.group(1)) for m in _GVC_FIELD_RE.finditer(rest)]
    for i, (pos, num) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(rest)
        fields.append((num, rest[pos + 3:end]))

    remittance_parts: list[str] = []
    name_parts: list[str] = []
    account = bic = None
    for num, value in fields:
        n = int(num)
        if n == 0:
            result.additional.append(f"posting text: {_clean(value)}")
        elif n == 10:
            result.additional.append(f"primanota: {_clean(value)}")
        elif 20 <= n <= 29 or 60 <= n <= 63:
            remittance_parts.append(value)  # joined raw: code words split mid-word
        elif n == 30:
            bic = _clean(value) or None
        elif n == 31:
            account = _clean(value) or None
        elif n in (32, 33):
            name_parts.append(_clean(value))
        elif n == 34:
            result.additional.append(f"text key extension: {_clean(value)}")
        else:
            result.additional.append(f"?{num}: {_clean(value)}")

    joined = "".join(remittance_parts)
    # extract SEPA code words from the rewrapped remittance block
    words = _SEPA_WORD_RE.split(joined)
    free_prefix = words[0].strip()
    svwz = None
    for word, value in zip(words[1::2], words[2::2]):
        value = value.strip()
        if word == "EREF":
            result.end_to_end_id = value or result.end_to_end_id
        elif word == "KREF":
            result.additional.append(f"customer ref (KREF): {value}")
        elif word == "MREF":
            result.mandate_id = value or result.mandate_id
        elif word == "CRED":
            result.additional.append(f"creditor id (CRED): {value}")
        elif word == "DEBT":
            result.additional.append(f"debtor id (DEBT): {value}")
        elif word == "SVWZ":
            svwz = value
        elif word in ("ABWA", "ABWE"):
            result.additional.append(f"deviating party ({word}): {value}")
        elif word == "BIC":
            bic = bic or value
        elif word == "IBAN":
            account = account or value
    if svwz:
        result.remittance.append(_clean(svwz))
    elif free_prefix and not result.remittance:
        result.remittance.append(_clean(free_prefix))
    if free_prefix and svwz:
        result.additional.append(f"pre-SEPA text: {_clean(free_prefix)}")

    name = " ".join(p for p in name_parts if p) or None
    if name or account or bic:
        result.counterparty = Counterparty(name=name, account=account, bic=bic)
    return result
