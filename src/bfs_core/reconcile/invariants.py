"""Balance reconciliation engine — INV-1..INV-6 and the arithmetic edge cases.

Sign model (RECONCILIATION-REQUIREMENTS.md §1): balances and movements are signed
via CreditDebit; reversals never flip signs. INV-4 (page chaining) is enforced by
the MT940 reader at merge time; INV-7/INV-8 (conversion/round-trip conservation)
are enforced by the conversion engine using ReconciliationResult equality.

Mismatches are never hidden or repaired — they surface as E_RECON_MISMATCH.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from bfs_core.errors import (
    E_BALANCE_CURRENCY_MISMATCH,
    E_RECON_MISMATCH,
    W_CURRENCY_DECIMALS,
    W_DATE_OUT_OF_PERIOD,
    W_DUPLICATE_ENTRY,
    W_ENTRY_CURRENCY_DIFFERS,
    W_SEQUENCE_GAP,
    W_SUMMARY_MISMATCH,
)
from bfs_core.model import (
    CURRENCY_DECIMALS,
    CreditDebit,
    DiagnosticReport,
    EntryStatus,
    Statement,
    decimal_places,
)


@dataclass
class ReconciliationResult:
    """Computed statement figures plus pass/fail. The quantity tuple
    (opening, closing, credits, debits, counts, currency) is the INV-7 conservation set."""

    passed: bool
    currency: str
    opening_declared: Decimal
    closing_declared: Decimal
    closing_computed: Decimal
    total_credits: Decimal
    total_debits: Decimal          # positive magnitude
    credit_count: int
    debit_count: int
    transaction_count: int         # booked entries included in INV-1
    excluded_count: int            # non-BOOK or foreign-currency entries
    report: DiagnosticReport = field(default_factory=DiagnosticReport)

    def conservation_key(self) -> tuple:
        return (
            self.currency, self.opening_declared, self.closing_declared,
            self.total_credits, self.total_debits,
            self.credit_count, self.debit_count, self.transaction_count,
        )


def reconcile_statement(s: Statement) -> ReconciliationResult:
    report = DiagnosticReport()
    where = f"statement {s.statement_id!r}"

    # INV-2 / E8: every balance must share one currency.
    balances = [("opening", s.opening_balance), ("closing", s.closing_balance)]
    if s.closing_available:
        balances.append(("closing available", s.closing_available))
    balances += [("forward available", b) for b in s.forward_available]
    balances += [(f"balance {code}", b) for code, b in s.other_balances]
    currencies = {b.currency for _, b in balances}
    if len(currencies) > 1:
        report.error(E_BALANCE_CURRENCY_MISMATCH, where=where,
                     detail=", ".join(f"{name}={b.currency}" for name, b in balances))

    currency = s.opening_balance.currency

    # Movement aggregation (INV-1 inputs) with E6/INV-3 exclusions.
    total_credits = Decimal(0)
    total_debits = Decimal(0)
    credit_count = debit_count = 0
    excluded = 0
    seen: dict[tuple, int] = {}
    for i, t in enumerate(s.transactions, 1):
        loc = f"{where}, entry {i}"
        if t.status is not EntryStatus.BOOK:
            excluded += 1        # W_NON_BOOKED_ENTRY already emitted by the reader
            continue
        if t.currency is not None and t.currency != currency:
            report.warning(W_ENTRY_CURRENCY_DIFFERS, value=t.currency,
                           detail=currency, where=loc)
            excluded += 1
            continue
        # E9: decimal places vs ISO 4217 minor units.
        allowed = CURRENCY_DECIMALS.get(currency, 2)
        if decimal_places(t.amount) > allowed:
            report.warning(W_CURRENCY_DECIMALS, value=str(t.amount),
                           detail=f"the {allowed} decimal places ISO 4217", where=loc)
        # E7: duplicate detection (informational; arithmetic unaffected).
        key = (t.value_date, t.booking_date, t.credit_debit, t.amount,
               t.customer_reference, t.bank_reference)
        if key in seen:
            report.warning(W_DUPLICATE_ENTRY, where=loc,
                           detail=f"same date/amount/references as entry {seen[key]}")
        else:
            seen[key] = i
        # INV-6: dates inside the statement period when declared.
        if s.from_datetime and t.value_date < s.from_datetime.date():
            report.warning(W_DATE_OUT_OF_PERIOD, value=t.value_date.isoformat(), where=loc)
        if s.to_datetime and t.value_date > s.to_datetime.date():
            report.warning(W_DATE_OUT_OF_PERIOD, value=t.value_date.isoformat(), where=loc)

        if t.credit_debit is CreditDebit.CREDIT:
            total_credits += t.amount
            credit_count += 1
        else:
            total_debits += t.amount
            debit_count += 1

    if s.closing_balance.date < s.opening_balance.date:
        report.warning(W_DATE_OUT_OF_PERIOD, value=s.closing_balance.date.isoformat(),
                       where=f"{where}: closing balance date precedes opening balance date")

    opening = s.opening_balance.signed()
    closing_declared = s.closing_balance.signed()
    closing_computed = opening + total_credits - total_debits

    # INV-1 with INV-3 escalation: exclusions make the sum non-authoritative.
    if closing_computed != closing_declared:
        diff = closing_declared - closing_computed
        detail = (f"opening {opening} {currency} + credits {total_credits} "
                  f"- debits {total_debits} = {closing_computed}, but the statement "
                  f"declares closing {closing_declared} (difference {diff})")
        if excluded:
            detail += f"; {excluded} entr{'y was' if excluded == 1 else 'ies were'} excluded (non-booked or foreign currency)"
        report.error(E_RECON_MISMATCH, detail=detail)

    # INV-5: bank-declared summary cross-check.
    if s.summary is not None:
        sm = s.summary
        booked = credit_count + debit_count
        checks = [
            ("entry count", sm.total_count, booked + excluded if sm.total_count is not None else None),
            ("credit count", sm.credit_count, credit_count),
            ("credit sum", sm.credit_sum, total_credits),
            ("debit count", sm.debit_count, debit_count),
            ("debit sum", sm.debit_sum, total_debits),
        ]
        for name, declared, computed in checks:
            if declared is not None and computed is not None and declared != computed:
                report.warning(W_SUMMARY_MISMATCH,
                               detail=f"{name}: statement declares {declared}, computed {computed}")
        if sm.net_amount is not None and sm.net_credit_debit is not None:
            declared_net = sm.net_amount * sm.net_credit_debit.sign
            computed_net = total_credits - total_debits
            if declared_net != computed_net:
                report.warning(W_SUMMARY_MISMATCH,
                               detail=f"net movement: statement declares {declared_net}, computed {computed_net}")

    return ReconciliationResult(
        passed=not report.has_errors,
        currency=currency,
        opening_declared=opening,
        closing_declared=closing_declared,
        closing_computed=closing_computed,
        total_credits=total_credits,
        total_debits=total_debits,
        credit_count=credit_count,
        debit_count=debit_count,
        transaction_count=credit_count + debit_count,
        excluded_count=excluded,
        report=report,
    )


def check_sequence_gaps(statements: list[Statement]) -> DiagnosticReport:
    """E12: warn about statement-number gaps per account across a batch."""
    report = DiagnosticReport()
    by_account: dict[str, list[Statement]] = {}
    for s in statements:
        by_account.setdefault(s.account_id_display, []).append(s)
    for account, group in by_account.items():
        numbered = sorted(
            (s for s in group if s.statement_number is not None),
            key=lambda s: s.statement_number,
        )
        for prev, nxt in zip(numbered, numbered[1:], strict=False):
            gap = nxt.statement_number - prev.statement_number
            if gap > 1:
                report.warning(
                    W_SEQUENCE_GAP,
                    detail=f"account {account}: statement {prev.statement_number} is followed by "
                           f"{nxt.statement_number} ({gap - 1} missing)")
    return report
