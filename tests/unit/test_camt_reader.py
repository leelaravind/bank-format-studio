"""P1-M3 tests: camt.053 readers vs the 7 public samples + synthetic error cases."""

from decimal import Decimal
from pathlib import Path

import pytest

from bfs_core.camt import read_camt053
from bfs_core.errors import (
    E_CAMT_NOT_CAMT053,
    E_CAMT_SCHEMA_INVALID,
    E_CAMT_UNSUPPORTED_VERSION,
    E_XML_DTD_FORBIDDEN,
    E_XML_NOT_WELL_FORMED,
    BfsError,
)
from bfs_core.model import CreditDebit

PUBLIC = Path(__file__).resolve().parents[2] / "sample-data" / "public" / "camt053"

PUBLIC_FILES = {
    "iso20022org-official-example_camt.053.001.02.xml": "camt.053.001.02",
    "genkgo-camt_v2-minimal-statement_camt.053.001.02.xml": "camt.053.001.02",
    "genkgo-camt_v2-all-balance-types_camt.053.001.02.xml": "camt.053.001.02",
    "genkgo-camt_v2-multiple-statements_camt.053.001.02.xml": "camt.053.001.02",
    "genkgo-camt_v2-five-decimal-amounts_camt.053.001.02.xml": "camt.053.001.02",
    "genkgo-camt_v2-party-ids-remittance_camt.053.001.02.xml": "camt.053.001.02",
    "genkgo-camt_v8-statement_camt.053.001.08.xml": "camt.053.001.08",
}


@pytest.mark.parametrize("name", sorted(PUBLIC_FILES))
def test_public_sample_reads(name):
    statements, report = read_camt053((PUBLIC / name).read_bytes())
    assert not report.has_errors, [d.message for d in report.errors]
    assert statements, "expected at least one statement"
    for s in statements:
        assert s.statement_id
        assert s.account_currency
        assert s.opening_balance is not None and s.closing_balance is not None
        assert s.source_format == PUBLIC_FILES[name]


def test_official_example_entries_map_details():
    # The official example has 3 entries (TxDtls counts 1/0/1) — no multi-TxDtls
    # batch; synthetic fixture C08 covers batches. Assert detail fields merged up.
    data = (PUBLIC / "iso20022org-official-example_camt.053.001.02.xml").read_bytes()
    statements, report = read_camt053(data)
    s = statements[0]
    assert len(s.transactions) == 3
    assert all(not t.details for t in s.transactions)
    assert any(t.counterparty or t.end_to_end_id or t.bank_reference for t in s.transactions)


def test_multiple_statements_sample():
    data = (PUBLIC / "genkgo-camt_v2-multiple-statements_camt.053.001.02.xml").read_bytes()
    statements, _ = read_camt053(data)
    assert len(statements) > 1


def test_v8_reversal_and_party_unwrap():
    data = (PUBLIC / "genkgo-camt_v8-statement_camt.053.001.08.xml").read_bytes()
    statements, report = read_camt053(data)
    assert not report.has_errors
    s = statements[0]
    assert s.source_format == "camt.053.001.08"
    assert any(t.remittance_unstructured or t.counterparty for t in s.transactions)


def test_unsupported_version_rejected():
    doc = (b'<?xml version="1.0"?>'
           b'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.14">'
           b"<BkToCstmrStmt/></Document>")
    with pytest.raises(BfsError) as e:
        read_camt053(doc)
    assert e.value.code == E_CAMT_UNSUPPORTED_VERSION


def test_non_camt_rejected():
    with pytest.raises(BfsError) as e:
        read_camt053(b'<?xml version="1.0"?><Document xmlns="urn:example:other"/>')
    assert e.value.code == E_CAMT_NOT_CAMT053


def test_malformed_xml_rejected():
    with pytest.raises(BfsError) as e:
        read_camt053(b"<Document><unclosed>")
    assert e.value.code == E_XML_NOT_WELL_FORMED


def test_dtd_rejected():
    doc = (b'<?xml version="1.0"?><!DOCTYPE Document [<!ENTITY x "y">]>'
           b'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"/>')
    with pytest.raises(BfsError) as e:
        read_camt053(doc)
    assert e.value.code == E_XML_DTD_FORBIDDEN


def test_schema_invalid_reports_xpath_errors():
    # Valid namespace, wrong structure: missing GrpHdr and mandatory children.
    doc = (b'<?xml version="1.0"?>'
           b'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">'
           b"<BkToCstmrStmt><Stmt><Id>X</Id></Stmt></BkToCstmrStmt></Document>")
    statements, report = read_camt053(doc)
    assert statements == []
    assert report.has_errors
    assert all(d.code == E_CAMT_SCHEMA_INVALID for d in report.errors)
    assert any(d.location for d in report.errors), "expected XPath locations"


def test_extra_decimals_kept_exact():
    # Despite its upstream name, this fixture carries 3-decimal amounts (e.g. 18.150);
    # assert sub-cent precision survives exactly, trailing zero included.
    data = (PUBLIC / "genkgo-camt_v2-five-decimal-amounts_camt.053.001.02.xml").read_bytes()
    statements, _ = read_camt053(data)
    amounts = [t.amount for s in statements for t in s.transactions]
    amounts += [s.opening_balance.amount for s in statements]
    amounts += [s.closing_balance.amount for s in statements]
    three_dp = [a for a in amounts if "." in str(a) and len(str(a).split(".")[1]) == 3]
    assert three_dp, f"expected 3-decimal amounts preserved exactly, got {amounts}"
    assert any(str(a).endswith("0") for a in three_dp), "trailing zero must survive"


def test_entry_sign_semantics():
    data = (PUBLIC / "genkgo-camt_v2-minimal-statement_camt.053.001.02.xml").read_bytes()
    statements, _ = read_camt053(data)
    for s in statements:
        for t in s.transactions:
            assert (t.signed() > 0) == (t.credit_debit is CreditDebit.CREDIT) or t.amount == Decimal(0)
