"""Version-neutral normalized model bridging MT940 / camt.053 / CSV.

Field semantics and loss analysis: spec/DATA-MAPPING-RESEARCH.md.
Amounts are unsigned Decimals with an explicit credit/debit flag; signed values
are derived only at boundaries (CSV) and in reconciliation arithmetic.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


class CreditDebit(enum.Enum):
    CREDIT = "C"
    DEBIT = "D"

    @property
    def sign(self) -> int:
        return 1 if self is CreditDebit.CREDIT else -1


class EntryStatus(enum.Enum):
    BOOK = "BOOK"
    PDNG = "PDNG"
    INFO = "INFO"


@dataclass(frozen=True)
class Balance:
    credit_debit: CreditDebit
    date: date
    currency: str
    amount: Decimal  # always >= 0

    def signed(self) -> Decimal:
        return self.amount * self.credit_debit.sign

    @staticmethod
    def from_signed(value: Decimal, on: date, currency: str) -> "Balance":
        cd = CreditDebit.CREDIT if value >= 0 else CreditDebit.DEBIT
        return Balance(credit_debit=cd, date=on, currency=currency, amount=abs(value))


@dataclass(frozen=True)
class Counterparty:
    name: str | None = None
    account: str | None = None       # IBAN or other id
    bic: str | None = None
    is_agent: bool = False           # camt .08 Party40Choice/Agt arm

    def is_empty(self) -> bool:
        return not (self.name or self.account or self.bic)


@dataclass(frozen=True)
class BankTransactionCode:
    domain: str | None = None
    family: str | None = None
    sub_family: str | None = None
    proprietary: str | None = None
    proprietary_issuer: str | None = None


@dataclass
class Transaction:
    """One movement. For camt batch entries (E13) the entry-level Transaction is
    authoritative for reconciliation and `details` holds the per-TxDtls breakdown."""

    value_date: date
    credit_debit: CreditDebit
    amount: Decimal                      # unsigned
    booking_date: date | None = None
    is_reversal: bool = False
    currency: str | None = None          # None = statement currency
    funds_code: str | None = None
    swift_tx_type: str | None = None     # e.g. NTRF (GATE-1 family)
    btc: BankTransactionCode | None = None
    customer_reference: str | None = None  # NONREF kept verbatim (locked decision)
    bank_reference: str | None = None
    end_to_end_id: str | None = None
    mandate_id: str | None = None
    supplementary_details: str | None = None
    counterparty: Counterparty | None = None
    remittance_unstructured: tuple[str, ...] = ()
    creditor_reference: str | None = None
    purpose_code: str | None = None
    return_reason: str | None = None
    charges_amount: Decimal | None = None
    instructed_amount: Decimal | None = None
    instructed_currency: str | None = None
    exchange_rate: Decimal | None = None
    entry_reference: str | None = None
    status: EntryStatus = EntryStatus.BOOK
    additional_info: str | None = None
    raw_86: str | None = None            # audit-only; never required for conversion
    details: tuple["Transaction", ...] = ()

    def signed(self) -> Decimal:
        """Signed movement. Reversal does NOT flip the sign — camt CdtDbtInd and
        the GATE-1 RD/RC mapping already encode the movement direction."""
        return self.amount * self.credit_debit.sign


@dataclass
class Statement:
    statement_id: str
    account_currency: str
    opening_balance: Balance
    closing_balance: Balance
    account_iban: str | None = None
    account_other_id: str | None = None
    account_raw: str | None = None       # verbatim :25: content for audit
    related_reference: str | None = None
    statement_number: int | None = None
    sequence_number: int | None = None
    page_count: int | None = None        # populated when MT940 pages were merged
    electronic_seq_number: int | None = None
    creation_datetime: datetime | None = None
    from_datetime: datetime | None = None
    to_datetime: datetime | None = None
    opening_is_intermediate: bool = False   # :60M:
    closing_is_intermediate: bool = False   # :62M:
    closing_available: Balance | None = None            # :64: / CLAV
    forward_available: tuple[Balance, ...] = ()         # :65: / FWAV
    other_balances: tuple[tuple[str, Balance], ...] = ()  # (type code, balance)
    transactions: list[Transaction] = field(default_factory=list)
    additional_info: str | None = None
    source_format: str = ""

    @property
    def account_id_display(self) -> str:
        return self.account_iban or self.account_other_id or self.account_raw or "?"

    def booked_transactions(self) -> list[Transaction]:
        return [t for t in self.transactions if t.status is EntryStatus.BOOK]
