"""P1-M4 tests: INV-1..6, E1/E3/E4/E7/E8/E9/E10/E12 arithmetic behaviours.

INV-4 (page chain) is covered in test_mt940_reader.py; INV-7/8 in the golden suite.
"""

from datetime import date, datetime
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
    Balance,
    CreditDebit,
    EntryStatus,
    Statement,
    Transaction,
    TransactionsSummary,
)
from bfs_core.reconcile import check_sequence_gaps, reconcile_statement

D = Decimal
C, DB = CreditDebit.CREDIT, CreditDebit.DEBIT


def stmt(opening="100.00", closing="100.00", opening_cd=C, closing_cd=C,
         transactions=(), currency="EUR", number=1, **kw) -> Statement:
    return Statement(
        statement_id=f"SYNTH-R{number}",
        account_iban="DE75512108001245126199",
        account_currency=currency,
        statement_number=number,
        opening_balance=Balance(opening_cd, date(2026, 1, 2), currency, D(opening)),
        closing_balance=Balance(closing_cd, date(2026, 1, 3), currency, D(closing)),
        transactions=list(transactions),
        source_format="test",
        **kw,
    )


def tx(amount, cd=C, status=EntryStatus.BOOK, currency=None, reversal=False,
       value=date(2026, 1, 3), booking=None, cref=None, bref=None) -> Transaction:
    return Transaction(value_date=value, booking_date=booking, credit_debit=cd,
                       amount=D(amount), status=status, currency=currency,
                       is_reversal=reversal, customer_reference=cref, bank_reference=bref)


class TestInv1:
    def test_balanced_statement_passes(self):
        r = reconcile_statement(stmt(closing="150.00", transactions=[tx("70.00"), tx("20.00", DB)]))
        assert r.passed
        assert r.total_credits == D("70.00") and r.total_debits == D("20.00")
        assert r.closing_computed == r.closing_declared == D("150.00")

    def test_zero_transactions_e1(self):
        r = reconcile_statement(stmt())
        assert r.passed and r.transaction_count == 0

    def test_mismatch_fails_with_diff_e10(self):
        r = reconcile_statement(stmt(closing="160.00", transactions=[tx("50.00")]))
        assert not r.passed
        assert any(d.code == E_RECON_MISMATCH and "difference 10.00" in d.message
                   for d in r.report.errors)

    def test_reversals_e3(self):
        # RD (credit-direction) +20, RC (debit-direction) -5
        r = reconcile_statement(stmt(closing="115.00",
                                     transactions=[tx("20.00", C, reversal=True),
                                                   tx("5.00", DB, reversal=True)]))
        assert r.passed

    def test_overdraft_crossing_zero_e4(self):
        s = stmt(opening="50.00", closing="30.00", opening_cd=C, closing_cd=DB,
                 transactions=[tx("80.00", DB)])
        r = reconcile_statement(s)
        assert r.passed
        assert r.closing_declared == D("-30.00")

    def test_large_amount_exact_e14(self):
        s = stmt(opening="0.00", closing="999999999999999", currency="JPY",
                 transactions=[tx("999999999999999", currency=None)])
        s.opening_balance = Balance(C, date(2026, 1, 2), "JPY", D("0"))
        s.closing_balance = Balance(C, date(2026, 1, 3), "JPY", D("999999999999999"))
        r = reconcile_statement(s)
        assert r.passed
        assert "E" not in str(r.closing_computed)  # no scientific notation


class TestExclusions:
    def test_non_booked_excluded_e6(self):
        r = reconcile_statement(stmt(transactions=[tx("10.00", status=EntryStatus.PDNG)]))
        assert r.passed  # closing unchanged because pending excluded
        assert r.excluded_count == 1

    def test_foreign_currency_warns_and_fails_recon_inv3(self):
        r = reconcile_statement(stmt(closing="120.00", transactions=[tx("20.00", currency="USD")]))
        assert W_ENTRY_CURRENCY_DIFFERS in r.report.codes()
        assert not r.passed
        assert any("excluded" in d.message for d in r.report.errors)


class TestWarnings:
    def test_duplicate_entries_e7(self):
        r = reconcile_statement(stmt(closing="120.00",
                                     transactions=[tx("10.00", cref="A"), tx("10.00", cref="A")]))
        assert r.passed  # arithmetic unaffected
        assert W_DUPLICATE_ENTRY in r.report.codes()

    def test_jpy_decimals_e9(self):
        s = stmt(opening="0", closing="10.5", currency="JPY", transactions=[tx("10.5")])
        s.opening_balance = Balance(C, date(2026, 1, 2), "JPY", D("0"))
        s.closing_balance = Balance(C, date(2026, 1, 3), "JPY", D("10.5"))
        r = reconcile_statement(s)
        assert W_CURRENCY_DECIMALS in r.report.codes()

    def test_currency_mismatch_e8(self):
        s = stmt()
        s.closing_balance = Balance(C, date(2026, 1, 3), "USD", D("100.00"))
        r = reconcile_statement(s)
        assert not r.passed
        assert E_BALANCE_CURRENCY_MISMATCH in r.report.codes()

    def test_dates_outside_period_inv6(self):
        s = stmt(closing="110.00", transactions=[tx("10.00", value=date(2026, 3, 1))])
        s.from_datetime = datetime(2026, 1, 1)
        s.to_datetime = datetime(2026, 1, 31)
        r = reconcile_statement(s)
        assert W_DATE_OUT_OF_PERIOD in r.report.codes()


class TestSummaryInv5:
    def test_summary_match_silent(self):
        s = stmt(closing="130.00", transactions=[tx("40.00"), tx("10.00", DB)])
        s.summary = TransactionsSummary(total_count=2, credit_count=1, credit_sum=D("40.00"),
                                        debit_count=1, debit_sum=D("10.00"))
        r = reconcile_statement(s)
        assert W_SUMMARY_MISMATCH not in r.report.codes()

    def test_summary_mismatch_warns(self):
        s = stmt(closing="130.00", transactions=[tx("40.00"), tx("10.00", DB)])
        s.summary = TransactionsSummary(credit_sum=D("99.00"))
        r = reconcile_statement(s)
        assert r.passed  # warning, not arithmetic failure
        assert W_SUMMARY_MISMATCH in r.report.codes()


class TestSequenceGaps:
    def test_gap_warns_e12(self):
        report = check_sequence_gaps([stmt(number=1), stmt(number=3)])
        assert W_SEQUENCE_GAP in report.codes()

    def test_contiguous_silent(self):
        report = check_sequence_gaps([stmt(number=1), stmt(number=2)])
        assert report.codes() == []


class TestPropertyStyle:
    def test_generated_statements_reconcile_by_construction(self):
        # Deterministic pseudo-random statements built to satisfy INV-1 exactly.
        import random
        rng = random.Random(42)
        for case in range(25):
            opening = D(rng.randint(-10_000_00, 10_000_00)) / 100
            txs = []
            running = opening
            for _ in range(rng.randint(0, 30)):
                cents = D(rng.randint(1, 500_000)) / 100
                cd = C if rng.random() < 0.5 else DB
                txs.append(tx(str(cents), cd))
                running += cents * cd.sign
            s = stmt(transactions=txs)
            s.opening_balance = Balance.from_signed(opening, date(2026, 1, 2), "EUR")
            s.closing_balance = Balance.from_signed(running, date(2026, 1, 3), "EUR")
            r = reconcile_statement(s)
            assert r.passed, f"case {case}: {r.report.codes()}"
