"""P1-M1 unit tests: model semantics, money rules, serialization round-trip."""

import json
from datetime import date
from decimal import Decimal

import pytest

from bfs_core.errors import BfsError
from bfs_core.model import (
    Balance,
    Counterparty,
    CreditDebit,
    Statement,
    Transaction,
    ensure_decimal,
    format_swift_amount,
    parse_swift_amount,
    statement_from_dict,
    statement_to_dict,
    validate_currency,
)


def make_statement() -> Statement:
    return Statement(
        statement_id="SYNTH-0001",
        account_iban="DE75512108001245126199",  # synthetic test IBAN
        account_currency="EUR",
        statement_number=1,
        opening_balance=Balance(CreditDebit.CREDIT, date(2026, 1, 2), "EUR", Decimal("1000.00")),
        closing_balance=Balance(CreditDebit.CREDIT, date(2026, 1, 3), "EUR", Decimal("1150.00")),
        transactions=[
            Transaction(value_date=date(2026, 1, 3), credit_debit=CreditDebit.CREDIT,
                        amount=Decimal("200.00"), customer_reference="NONREF"),
            Transaction(value_date=date(2026, 1, 3), credit_debit=CreditDebit.DEBIT,
                        amount=Decimal("50.00"), is_reversal=True,
                        counterparty=Counterparty(name="Acme Tooling GmbH")),
        ],
        source_format="test",
    )


class TestBalance:
    def test_signed_credit_positive_debit_negative(self):
        c = Balance(CreditDebit.CREDIT, date(2026, 1, 1), "EUR", Decimal("10.5"))
        d = Balance(CreditDebit.DEBIT, date(2026, 1, 1), "EUR", Decimal("10.5"))
        assert c.signed() == Decimal("10.5")
        assert d.signed() == Decimal("-10.5")

    def test_from_signed_overdraft(self):
        b = Balance.from_signed(Decimal("-3.14"), date(2026, 1, 1), "EUR")
        assert b.credit_debit is CreditDebit.DEBIT
        assert b.amount == Decimal("3.14")


class TestTransactionSign:
    def test_reversal_does_not_flip_sign(self):
        # GATE-1: RD maps to CREDIT+reversal, RC to DEBIT+reversal; sign follows credit_debit.
        rd = Transaction(value_date=date(2026, 1, 1), credit_debit=CreditDebit.CREDIT,
                         amount=Decimal("5"), is_reversal=True)
        rc = Transaction(value_date=date(2026, 1, 1), credit_debit=CreditDebit.DEBIT,
                         amount=Decimal("5"), is_reversal=True)
        assert rd.signed() == Decimal("5")
        assert rc.signed() == Decimal("-5")


class TestMoney:
    def test_float_rejected(self):
        with pytest.raises(BfsError):
            ensure_decimal(1.23)

    def test_swift_amount_parsing_variants(self):
        assert parse_swift_amount("123,45") == Decimal("123.45")
        assert parse_swift_amount("6800,") == Decimal("6800")
        assert parse_swift_amount("000000000025,00") == Decimal("25.00")
        assert parse_swift_amount("11,8") == Decimal("11.8")

    def test_swift_amount_rejects_garbage(self):
        for bad in ("", "12.34", "1,2,3", "abc", "-5,00", "1234567890123456"):
            with pytest.raises(BfsError):
                parse_swift_amount(bad)

    def test_swift_amount_roundtrip_format(self):
        assert format_swift_amount(Decimal("123.45")) == "123,45"
        assert format_swift_amount(Decimal("6800")) == "6800,"
        with pytest.raises(BfsError):
            format_swift_amount(Decimal("-1"))

    def test_currency_validation(self):
        assert validate_currency("eur") == "EUR"
        for bad in ("EU0", "EURO", "", "12A"):
            with pytest.raises(BfsError):
                validate_currency(bad)


class TestSerialization:
    def test_round_trip_preserves_statement(self):
        s = make_statement()
        d = statement_to_dict(s)
        s2 = statement_from_dict(json.loads(json.dumps(d)))
        assert statement_to_dict(s2) == d

    def test_serialization_is_deterministic(self):
        s = make_statement()
        a = json.dumps(statement_to_dict(s), sort_keys=True)
        b = json.dumps(statement_to_dict(make_statement()), sort_keys=True)
        assert a == b

    def test_decimals_serialized_as_strings(self):
        d = statement_to_dict(make_statement())
        assert d["opening_balance"]["amount"] == "1000.00"
        assert d["transactions"][0]["amount"] == "200.00"
