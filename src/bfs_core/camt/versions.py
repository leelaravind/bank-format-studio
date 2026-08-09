"""camt.053 version detection and the thin per-version adapter specs (GATE-2).

The normalized model is version-neutral; everything version-specific is captured
in a _VersionSpec consumed by the shared reader/writer cores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bfs_core.errors import E_CAMT_NOT_CAMT053, E_CAMT_UNSUPPORTED_VERSION, BfsError

NS_PREFIX = "urn:iso:std:iso:20022:tech:xsd:camt.053.001."

# GATE-2 verified enum for .02 (BalanceType12Code); .08 uses the external code set.
V02_BALANCE_CODES = frozenset(
    {"XPCD", "OPAV", "ITAV", "CLAV", "FWAV", "CLBD", "ITBD", "OPBD", "PRCD", "INFO"}
)


@dataclass(frozen=True)
class VersionSpec:
    key: str                      # "02" / "08"
    namespace: str
    schema_file: str
    party_wrapped: bool           # .08 Party40Choice (Pty|Agt) vs .02 direct PartyIdentification32
    bic_tag: str                  # "BIC" (.02) vs "BICFI" (.08)
    status_is_choice: bool        # .08 EntryStatus1Choice (Cd|Prtry) vs .02 enum
    balance_codes_closed: bool    # .02 closed enum vs .08 external code set
    has_pagination: bool          # .08 StmtPgntn


V02 = VersionSpec(
    key="02",
    namespace=NS_PREFIX + "02",
    schema_file="camt.053.001.02.xsd",
    party_wrapped=False,
    bic_tag="BIC",
    status_is_choice=False,
    balance_codes_closed=True,
    has_pagination=False,
)

V08 = VersionSpec(
    key="08",
    namespace=NS_PREFIX + "08",
    schema_file="camt.053.001.08.xsd",
    party_wrapped=True,
    bic_tag="BICFI",
    status_is_choice=True,
    balance_codes_closed=False,
    has_pagination=True,
)

SUPPORTED: dict[str, VersionSpec] = {V02.namespace: V02, V08.namespace: V08}


def detect_version(root_namespace: str) -> VersionSpec:
    spec = SUPPORTED.get(root_namespace)
    if spec is not None:
        return spec
    m = re.fullmatch(re.escape(NS_PREFIX) + r"(\d+)", root_namespace)
    if m:
        raise BfsError(E_CAMT_UNSUPPORTED_VERSION, value=f"camt.053.001.{m.group(1)}")
    raise BfsError(E_CAMT_NOT_CAMT053, value=root_namespace)
