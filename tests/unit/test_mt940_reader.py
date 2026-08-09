"""P1-M2 tests: MT940 reader vs synthetic cases and the 9 public fixtures."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from bfs_core.errors import (
    E_MT940_BAD_DC_MARK,
    E_MT940_MISSING_CLOSING,
    E_PAGE_CHAIN_BROKEN,
    W_DANGLING_INTERMEDIATE,
    W_ENTRY_DATE_YEAR_GUESSED,
    W_UNKNOWN_TAG,
    BfsError,
)
from bfs_core.model import CreditDebit
from bfs_core.mt940 import read_mt940

PUBLIC = Path(__file__).resolve().parents[2] / "sample-data" / "public" / "mt940"

BASIC = b""":20:SYNTH-0001
:25:DE75512108001245126199
:28C:1/1
:60F:C260102EUR1000,00
:61:2601030103C200,00NTRFNONREF//BANKREF1
:86:INVOICE 4711 ACME TOOLING GMBH
:61:2601030103D50,00NMSCCUSTREF1
:86:CARD PAYMENT SUPERMARKET
:62F:C260103EUR1150,00
"""


class TestBasicParsing:
    def test_basic_statement(self):
        statements, report = read_mt940(BASIC)
        assert len(statements) == 1
        s = statements[0]
        assert s.statement_id == "SYNTH-0001"
        assert s.account_iban == "DE75512108001245126199"
        assert s.statement_number == 1 and s.sequence_number == 1
        assert s.account_currency == "EUR"
        assert s.opening_balance.signed() == Decimal("1000.00")
        assert s.closing_balance.signed() == Decimal("1150.00")
        assert [t.signed() for t in s.transactions] == [Decimal("200.00"), Decimal("-50.00")]
        assert s.transactions[0].bank_reference == "BANKREF1"
        assert s.transactions[0].customer_reference == "NONREF"  # verbatim (locked)
        assert s.transactions[1].customer_reference == "CUSTREF1"
        assert not report.has_errors

    def test_gate1_reversal_marks(self):
        data = BASIC.replace(b"C200,00NTRF", b"RD200,00NTRF").replace(b"D50,00NMSC", b"RC50,00NMSC")
        statements, _ = read_mt940(data)
        t_rd, t_rc = statements[0].transactions
        assert t_rd.is_reversal and t_rd.credit_debit is CreditDebit.CREDIT
        assert t_rd.signed() == Decimal("200.00")
        assert t_rc.is_reversal and t_rc.credit_debit is CreditDebit.DEBIT
        assert t_rc.signed() == Decimal("-50.00")

    def test_gate1_invalid_mark_rejected(self):
        bad = BASIC.replace(b":61:2601030103C200,00", b":61:2601030103EC200,00")
        with pytest.raises(BfsError) as e:
            read_mt940(bad)
        assert e.value.code == E_MT940_BAD_DC_MARK

    def test_missing_closing_is_hard_error(self):
        truncated = BASIC.split(b":62F:")[0]
        with pytest.raises(BfsError) as e:
            read_mt940(truncated)
        assert e.value.code == E_MT940_MISSING_CLOSING

    def test_year_boundary_entry_date_warns(self):
        data = b""":20:SYNTH-YB
:25:DE75512108001245126199
:28C:1
:60F:C251231EUR100,00
:61:2601021230D10,00NMSCNONREF
:62F:C260102EUR90,00
"""
        statements, report = read_mt940(data)
        t = statements[0].transactions[0]
        assert t.value_date == date(2026, 1, 2)
        assert t.booking_date == date(2025, 12, 30)
        assert W_ENTRY_DATE_YEAR_GUESSED in report.codes()


class TestPageChains:
    TWO_PAGES = b""":20:SYNTH-PAGES
:25:DE75512108001245126199
:28C:7/1
:60F:C260101EUR500,00
:61:2601020102D100,00NMSCNONREF
:62M:C260102EUR400,00
:20:SYNTH-PAGES
:25:DE75512108001245126199
:28C:7/2
:60M:C260102EUR400,00
:61:2601030103C50,00NTRFNONREF
:62F:C260103EUR450,00
"""

    def test_chain_merged(self):
        statements, report = read_mt940(self.TWO_PAGES)
        assert len(statements) == 1
        s = statements[0]
        assert s.page_count == 2
        assert len(s.transactions) == 2
        assert s.opening_balance.signed() == Decimal("500.00")
        assert s.closing_balance.signed() == Decimal("450.00")
        assert not s.closing_is_intermediate
        assert W_DANGLING_INTERMEDIATE not in report.codes()

    def test_broken_chain_rejected(self):
        broken = self.TWO_PAGES.replace(b":60M:C260102EUR400,00", b":60M:C260102EUR999,00")
        with pytest.raises(BfsError) as e:
            read_mt940(broken)
        assert e.value.code == E_PAGE_CHAIN_BROKEN


class TestStructured86:
    def test_nl_slash_codewords(self):
        data = b""":20:SYNTH-NL
:25:NL44RABO0123456789
:28C:100
:60F:C260101EUR250,00
:61:2601020102C75,00NTRFEREF//B1
:86:/EREF/E2E-REF-001/ORDP//NAME/Jane Example/IBAN/NL91ABNA0417164300/REMI/Invoice 77
:62F:C260102EUR325,00
"""
        statements, _ = read_mt940(data)
        t = statements[0].transactions[0]
        assert t.end_to_end_id == "E2E-REF-001"
        assert t.counterparty and t.counterparty.name == "Jane Example"
        assert t.counterparty.account == "NL91ABNA0417164300"
        assert t.remittance_unstructured == ("Invoice 77",)

    def test_german_gvc(self):
        data = b""":20:SYNTH-DE
:25:12345678/1020304050
:28C:5
:60F:C260101EUR100,00
:61:2601020102C20,00NTRFNONREF
:86:166?00SEPA GUTSCHRIFT?10931?20EREF+E2E-42?21SVWZ+Rechnung 9?22 Teil 2?32Acme Tooling?33 GmbH?31DE75512108001245126199?30GENODEF1TST
:62F:C260102EUR120,00
"""
        statements, _ = read_mt940(data)
        t = statements[0].transactions[0]
        assert t.btc and t.btc.proprietary == "166"
        assert t.end_to_end_id == "E2E-42"
        assert t.counterparty and "Acme Tooling" in (t.counterparty.name or "")
        assert t.counterparty.account == "DE75512108001245126199"
        assert t.counterparty.bic == "GENODEF1TST"
        assert any("Rechnung 9" in r for r in t.remittance_unstructured)
        assert t.raw_86 is not None  # verbatim preserved for audit


PUBLIC_EXPECTATIONS = {
    # filename: (n statements after merge, total transactions, expect hard error code or None)
    "wolph-mt940-asnb.txt": (31, 8, None),   # 31 FIN messages, most zero-transaction
    "wolph-mt940-betterplace-sepa.sta": (2, 11, None),  # two accounts, both complete
    "wolph-mt940-cmxl-german.sta": (3, 16, None),
    "wolph-mt940-gv-codes-german.sta": (None, None, E_MT940_MISSING_CLOSING),
    "wolph-mt940-jejik-abnamro.sta": (2, 10, None),
    "wolph-mt940-jejik-ing.sta": (1, 7, None),
    "wolph-mt940-jejik-rabobank-iban.sta": (2, 4, None),
    "wolph-mt940-mbank.sta": (1, 3, None),
    "wolph-mt940-sberbank.sta": (1, 3, None),
}


@pytest.mark.parametrize("name", sorted(PUBLIC_EXPECTATIONS))
def test_public_fixture(name):
    n_statements, n_tx, error_code = PUBLIC_EXPECTATIONS[name]
    data = (PUBLIC / name).read_bytes()
    if error_code:
        with pytest.raises(BfsError) as e:
            read_mt940(data)
        assert e.value.code == error_code
        return
    statements, report = read_mt940(data)
    assert len(statements) == n_statements, f"{name}: {len(statements)} statements"
    assert sum(len(s.transactions) for s in statements) == n_tx
    for s in statements:
        assert s.opening_balance.currency == s.closing_balance.currency


def test_sberbank_ns_tags_warn_and_preserved():
    statements, report = read_mt940((PUBLIC / "wolph-mt940-sberbank.sta").read_bytes())
    assert W_UNKNOWN_TAG in report.codes()
    assert statements[0].additional_info  # :NS: payload preserved


def test_mbank_reconciles_by_movements():
    statements, _ = read_mt940((PUBLIC / "wolph-mt940-mbank.sta").read_bytes())
    s = statements[0]
    total = sum(t.signed() for t in s.transactions)
    assert s.opening_balance.signed() + total == s.closing_balance.signed()
