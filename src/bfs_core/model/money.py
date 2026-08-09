"""Exact-decimal money helpers. Binary floats are forbidden for monetary values."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from bfs_core.errors import E_BAD_CURRENCY, E_MT940_BAD_AMOUNT, BfsError

_CCY_RE = re.compile(r"^[A-Z]{3}$")

# ISO 4217 minor-unit exceptions used for the W_CURRENCY_DECIMALS check (E9).
# Not exhaustive of all currencies — covers the zero- and three-decimal sets;
# every currency not listed uses the default of 2.
CURRENCY_DECIMALS: dict[str, int] = {
    "BIF": 0, "CLP": 0, "DJF": 0, "GNF": 0, "ISK": 0, "JPY": 0, "KMF": 0,
    "KRW": 0, "PYG": 0, "RWF": 0, "UGX": 0, "UYI": 0, "VND": 0, "VUV": 0,
    "XAF": 0, "XOF": 0, "XPF": 0,
    "BHD": 3, "IQD": 3, "JOD": 3, "KWD": 3, "LYD": 3, "OMR": 3, "TND": 3,
}


def ensure_decimal(value: object, where: str = "") -> Decimal:
    """Accept Decimal/int/str; reject float to keep arithmetic exact."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise BfsError(E_MT940_BAD_AMOUNT, value=value, where=where, detail="boolean is not an amount")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        raise BfsError(E_MT940_BAD_AMOUNT, value=value, where=where,
                       detail="binary float amounts are forbidden; use Decimal or string")
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise BfsError(E_MT940_BAD_AMOUNT, value=value, where=where, detail=str(exc)) from exc
    raise BfsError(E_MT940_BAD_AMOUNT, value=value, where=where, detail=f"unsupported type {type(value).__name__}")


def parse_swift_amount(text: str, where: str = "") -> Decimal:
    """Parse an MT940 amount: comma decimal separator, optional bare trailing comma,
    optionally no comma at all, max 15 characters including the comma."""
    raw = text.strip()
    if not raw or len(raw) > 15 or not re.fullmatch(r"\d{1,15}(,\d{0,14})?", raw):
        raise BfsError(E_MT940_BAD_AMOUNT, value=text, where=where,
                       detail="expected digits with a comma decimal separator")
    normalized = raw.replace(",", ".")
    if normalized.endswith("."):
        normalized += "0"
    return Decimal(normalized)


def format_swift_amount(amount: Decimal) -> str:
    """Serialize a non-negative Decimal as an MT940 amount (comma separator,
    at least one decimal digit is not required — but a comma always present per 15d practice)."""
    if amount < 0:
        raise BfsError(E_MT940_BAD_AMOUNT, value=str(amount), where="serializer",
                       detail="MT940 amounts are unsigned; sign belongs in the D/C mark")
    text = format(amount, "f")
    if "." in text:
        int_part, frac = text.split(".")
        return f"{int_part},{frac}"
    return f"{text},"


def validate_currency(code: str, where: str = "") -> str:
    code = (code or "").strip().upper()
    if not _CCY_RE.fullmatch(code):
        raise BfsError(E_BAD_CURRENCY, value=code, where=where)
    return code


def decimal_places(amount: Decimal) -> int:
    exponent = amount.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0
