"""SWIFT :61: type code ↔ ISO Bank Transaction Code mapping (data-driven, best-effort)."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from bfs_core.model import BankTransactionCode


@lru_cache(maxsize=1)
def _tables() -> dict:
    data = (resources.files("bfs_core.convert") / "data" / "btc_map.json").read_text("utf-8")
    return json.loads(data)


def swift_to_btc(swift_code: str | None) -> BankTransactionCode | None:
    if not swift_code:
        return None
    entry = _tables()["swift_to_btc"].get(swift_code.upper())
    if entry is None:
        return None
    return BankTransactionCode(domain=entry["domain"], family=entry["family"],
                               sub_family=entry["sub_family"])


def btc_to_swift(btc: BankTransactionCode | None) -> str | None:
    """Returns a SWIFT 4-char code, or None when only the NMSC fallback applies
    (caller decides on the fallback and the loss note)."""
    if btc is None:
        return None
    if btc.proprietary and len(btc.proprietary) == 4 and btc.proprietary[0] in "NFS":
        return btc.proprietary.upper()
    if btc.domain and btc.family:
        return _tables()["btc_family_to_swift"].get(f"{btc.domain}/{btc.family}")
    return None
