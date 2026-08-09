"""Generate the synthetic fixture corpus (M01-M20, C01-C14, V01-V05) and freeze
golden cases (spec/FIXTURE-PLAN.md, spec/GOLDEN-CASE-REQUIREMENTS.md).

ALL DATA IS SYNTHETIC. IBANs/BICs/names are fictional test values.

Honest generation protocol:
- MT940 fixtures are hand-authored literals below (independent of our writer).
- Valid camt fixtures are built from hand-authored model definitions through the
  writer, which self-validates against the official XSD; deliberately-invalid
  camt fixtures are hand-authored literals.
- Expected reconciliation figures are AUTHORED literals; generation FAILS if the
  engine's computed figures disagree (independent cross-check, both directions).
- Golden expected outputs are frozen engine outputs, additionally verified by
  XSD self-validation (camt), reparse conservation (INV-7, enforced in-engine),
  and the authored figures. Golden tests then byte-compare forever.

Run:  python tools/gen_fixtures.py   (deterministic; rewrites tests/fixtures + tests/golden-cases)
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bfs_core.camt import V02, write_camt053  # noqa: E402
from bfs_core.convert import (  # noqa: E402
    FORMAT_CAMT_V02,
    FORMAT_CAMT_V08,
    FORMAT_CSV,
    FORMAT_MT940,
    ConversionInput,
    convert,
    read_input,
)
from bfs_core.csvio import write_csv  # noqa: E402
from bfs_core.model import (  # noqa: E402
    Balance,
    Counterparty,
    CreditDebit,
    EntryStatus,
    Statement,
    Transaction,
    TransactionsSummary,
    statement_to_dict,
)
from bfs_core.reconcile import reconcile_statement  # noqa: E402

D = Decimal
C, DB = CreditDebit.CREDIT, CreditDebit.DEBIT
CLOCK = datetime(2026, 1, 15, 10, 30)
FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden-cases"

IBAN = "DE75512108001245126199"  # synthetic
IBAN_NL = "NL91ABNA0417164300"   # synthetic


# --------------------------------------------------------------------------
# MT940 fixtures: hand-authored literals. Figures below each are authored too.
# --------------------------------------------------------------------------

def _mt940_header(sid: str, number: str = "1/1", account: str = IBAN) -> str:
    return f":20:{sid}\n:25:{account}\n:28C:{number}\n"


MT940_FIXTURES: dict[str, str] = {
    # M01 valid basic: 2 tx, credit+debit
    "M01": _mt940_header("SYNTH-M01")
    + ":60F:C260102EUR1000,00\n"
    + ":61:2601030103C200,00NTRFNONREF//B-1\n:86:INVOICE 4711 ACME TOOLING GMBH\n"
    + ":61:2601030103D50,00NMSCCUST-1\n:86:CARD PAYMENT SUPERMARKET\n"
    + ":62F:C260103EUR1150,00\n",
    # M02 volume: 12 tx mixed
    "M02": _mt940_header("SYNTH-M02")
    + ":60F:C260102EUR500,00\n"
    + "".join(
        f":61:26010{3 + i % 2}0103{'C' if i % 3 else 'D'}{10 + i},{i:02d}NTRFREF-{i}\n"
        f":86:PAYMENT {i}\n"
        for i in range(12))
    + ":62F:C260104EUR570,30\n",
    # M03 debit only
    "M03": _mt940_header("SYNTH-M03")
    + ":60F:C260102EUR300,00\n"
    + ":61:2601030103D10,00NMSCNONREF\n:86:FEE A\n"
    + ":61:2601030103D20,50NMSCNONREF\n:86:FEE B\n"
    + ":61:2601030103D30,00NCHGNONREF\n:86:FEE C\n"
    + ":62F:C260103EUR239,50\n",
    # M04 credit only
    "M04": _mt940_header("SYNTH-M04")
    + ":60F:D260102EUR100,00\n"
    + ":61:2601030103C60,00NTRFNONREF\n:86:SALARY PART 1\n"
    + ":61:2601030103C70,00NTRFNONREF\n:86:SALARY PART 2\n"
    + ":62F:C260103EUR30,00\n",
    # M05 zero transactions
    "M05": _mt940_header("SYNTH-M05")
    + ":60F:C260102EUR250,00\n:62F:C260102EUR250,00\n",
    # M06 malformed :61: line (invalid value date)
    "M06": _mt940_header("SYNTH-M06")
    + ":60F:C260102EUR100,00\n:61:26AB030103C10,00NTRFNONREF\n:62F:C260102EUR110,00\n",
    # M07 invalid currency
    "M07": _mt940_header("SYNTH-M07")
    + ":60F:C260102EU0100,00\n:62F:C260102EU0100,00\n",
    # M08 missing opening balance
    "M08": _mt940_header("SYNTH-M08")
    + ":61:2601030103C10,00NTRFNONREF\n:62F:C260103EUR10,00\n",
    # M09 missing closing balance (truncated)
    "M09": _mt940_header("SYNTH-M09")
    + ":60F:C260102EUR100,00\n:61:2601030103C10,00NTRFNONREF\n",
    # M10 duplicate transactions
    "M10": _mt940_header("SYNTH-M10")
    + ":60F:C260102EUR100,00\n"
    + ":61:2601030103D25,00NMSCDUP-1//BR-9\n:86:SAME PAYMENT\n"
    + ":61:2601030103D25,00NMSCDUP-1//BR-9\n:86:SAME PAYMENT\n"
    + ":62F:C260103EUR50,00\n",
    # M11 balance mismatch (declared closing wrong by 10)
    "M11": _mt940_header("SYNTH-M11")
    + ":60F:C260102EUR100,00\n"
    + ":61:2601030103C50,00NTRFNONREF\n:86:OK\n"
    + ":62F:C260103EUR160,00\n",
    # M12 two-page chain
    "M12": _mt940_header("SYNTH-M12", "7/1")
    + ":60F:C260101EUR500,00\n"
    + ":61:2601020102D100,00NMSCNONREF\n:86:PAGE1 PAYMENT\n"
    + ":62M:C260102EUR400,00\n"
    + _mt940_header("SYNTH-M12", "7/2")
    + ":60M:C260102EUR400,00\n"
    + ":61:2601030103C50,00NTRFNONREF\n:86:PAGE2 RECEIPT\n"
    + ":62F:C260103EUR450,00\n",
    # M13 reversals RD + RC
    "M13": _mt940_header("SYNTH-M13")
    + ":60F:C260102EUR100,00\n"
    + ":61:2601030103RD20,00NTRFNONREF\n:86:REVERSAL OF DEBIT\n"
    + ":61:2601030103RC5,00NTRFNONREF\n:86:REVERSAL OF CREDIT\n"
    + ":62F:C260103EUR115,00\n",
    # M14 German GVC structured :86:
    "M14": _mt940_header("SYNTH-M14", "5/1", "12345678/1020304050")
    + ":60F:C260102EUR100,00\n"
    + ":61:2601030103C20,00NTRFNONREF\n"
    + ":86:166?00SEPA GUTSCHRIFT?10931?20EREF+E2E-M14?21SVWZ+Rechnung 9\n"
    + "?22 Teil 2?32Acme Tooling?33 GmbH?31DE75512108001245126199?30GENO\n"
    + "DEF1TST\n"
    + ":62F:C260103EUR120,00\n",
    # M15 NL slash structured :86:
    "M15": _mt940_header("SYNTH-M15", "9/1", IBAN_NL)
    + ":60F:C260102EUR250,00\n"
    + ":61:2601030103C75,00NTRFEREF//B-15\n"
    + ":86:/EREF/E2E-M15/ORDP//NAME/Jane Example/IBAN/DE7551210800124512\n6199/REMI/Invoice 77\n"
    + ":62F:C260103EUR325,00\n",
    # M16 FIN block envelope
    "M16": "{1:F01TESTDEFFXXXX0000000000}{2:O940TESTDEFFXXXXN}{4:\n"
    + _mt940_header("SYNTH-M16")
    + ":60F:C260102EUR80,00\n"
    + ":61:2601030103C15,00NTRFNONREF\n:86:ENVELOPED PAYMENT\n"
    + ":62F:C260103EUR95,00\n-}",
    # M17 :64: and repeated :65:
    "M17": _mt940_header("SYNTH-M17")
    + ":60F:C260102EUR100,00\n"
    + ":61:2601030103C10,00NTRFNONREF\n:86:PAYMENT\n"
    + ":62F:C260103EUR110,00\n"
    + ":64:C260103EUR105,00\n"
    + ":65:C260104EUR110,00\n:65:C260105EUR110,00\n",
    # M18 unknown :NS: tag
    "M18": _mt940_header("SYNTH-M18")
    + ":60F:C260102EUR100,00\n"
    + ":61:2601030103C10,00NTRFNONREF\n:NS:22EXTRA BANK DATA\n"
    + ":62F:C260103EUR110,00\n",
    # M19 JPY (0-decimal currency) with decimals + big amount
    "M19": _mt940_header("SYNTH-M19")
    + ":60F:C260102JPY1000000,\n"
    + ":61:2601030103C999999999999,N559NONREF\n:86:LARGE TRANSFER\n"
    + ":61:2601030103D10,5NMSCNONREF\n:86:ODD JPY DECIMALS\n"
    + ":62F:C260103JPY1000999999989,\n",
    # M20 year-boundary entry date
    "M20": _mt940_header("SYNTH-M20")
    + ":60F:C251231EUR100,00\n"
    + ":61:2601021230D10,00NMSCNONREF\n:86:BOOKED IN DECEMBER\n"
    + ":62F:C260102EUR90,00\n",
}

# Authored expectations for VALID MT940 fixtures:
# (statements, booked tx, opening, credits, debits, closing, currency, recon passes, expected warning codes)
MT940_EXPECT: dict[str, dict] = {
    "M01": dict(n=1, tx=2, opening="1000.00", credits="200.00", debits="50.00", closing="1150.00", ccy="EUR", ok=True, warns=[]),
    "M02": dict(n=1, tx=12, opening="500.00", credits="128.48", debits="58.18", closing="570.30", ccy="EUR", ok=True, warns=[]),
    "M03": dict(n=1, tx=3, opening="300.00", credits="0", debits="60.50", closing="239.50", ccy="EUR", ok=True, warns=[]),
    "M04": dict(n=1, tx=2, opening="-100.00", credits="130.00", debits="0", closing="30.00", ccy="EUR", ok=True, warns=[]),
    "M05": dict(n=1, tx=0, opening="250.00", credits="0", debits="0", closing="250.00", ccy="EUR", ok=True, warns=[]),
    "M10": dict(n=1, tx=2, opening="100.00", credits="0", debits="50.00", closing="50.00", ccy="EUR", ok=True, warns=["W_DUPLICATE_ENTRY"]),
    "M11": dict(n=1, tx=1, opening="100.00", credits="50.00", debits="0", closing="160.00", ccy="EUR", ok=False, warns=[]),
    "M12": dict(n=1, tx=2, opening="500.00", credits="50.00", debits="100.00", closing="450.00", ccy="EUR", ok=True, warns=[]),
    "M13": dict(n=1, tx=2, opening="100.00", credits="20.00", debits="5.00", closing="115.00", ccy="EUR", ok=True, warns=[]),
    "M14": dict(n=1, tx=1, opening="100.00", credits="20.00", debits="0", closing="120.00", ccy="EUR", ok=True, warns=[]),
    "M15": dict(n=1, tx=1, opening="250.00", credits="75.00", debits="0", closing="325.00", ccy="EUR", ok=True, warns=[]),
    "M16": dict(n=1, tx=1, opening="80.00", credits="15.00", debits="0", closing="95.00", ccy="EUR", ok=True, warns=[]),
    "M17": dict(n=1, tx=1, opening="100.00", credits="10.00", debits="0", closing="110.00", ccy="EUR", ok=True, warns=[]),
    "M18": dict(n=1, tx=1, opening="100.00", credits="10.00", debits="0", closing="110.00", ccy="EUR", ok=True, warns=["W_UNKNOWN_TAG"]),
    "M19": dict(n=1, tx=2, opening="1000000", credits="999999999999", debits="10.5", closing="1000999999989", ccy="JPY", ok=False, warns=["W_CURRENCY_DECIMALS"]),
    "M20": dict(n=1, tx=1, opening="100.00", credits="0", debits="10.00", closing="90.00", ccy="EUR", ok=True, warns=["W_ENTRY_DATE_YEAR_GUESSED"]),
}
MT940_ERRORS: dict[str, str] = {
    "M06": "E_MT940_PARSE",
    "M07": "E_BAD_CURRENCY",
    "M08": "E_MT940_MISSING_OPENING",
    "M09": "E_MT940_MISSING_CLOSING",
}


# --------------------------------------------------------------------------
# camt fixtures: model definitions (valid → writer) + literal invalid files
# --------------------------------------------------------------------------

def _bal(cd, y, m, d_, ccy, amt) -> Balance:
    return Balance(cd, date(y, m, d_), ccy, D(amt))


def _stmt(sid: str, opening: Balance, closing: Balance, txs: list[Transaction],
          **kw) -> Statement:
    return Statement(
        statement_id=sid, account_iban=kw.pop("iban", IBAN),
        account_other_id=kw.pop("other_id", None),
        account_currency=opening.currency, statement_number=kw.pop("number", 1),
        opening_balance=opening, closing_balance=closing, transactions=txs,
        from_datetime=datetime(2026, 1, 1), to_datetime=datetime(2026, 1, 31),
        source_format="synthetic", **kw)


def _tx(amt, cd=C, **kw) -> Transaction:
    kw.setdefault("value_date", date(2026, 1, 3))
    kw.setdefault("booking_date", date(2026, 1, 3))
    kw.setdefault("swift_tx_type", "NTRF")
    return Transaction(credit_debit=cd, amount=D(amt), **kw)


CAMT_MODELS: dict[str, list[Statement]] = {
    "C01": [_stmt("SYNTH-C01",
                  _bal(C, 2026, 1, 2, "EUR", "1000.00"), _bal(C, 2026, 1, 3, "EUR", "1150.00"),
                  [_tx("200.00", C, end_to_end_id="E2E-C01-1",
                       counterparty=Counterparty(name="Acme Tooling GmbH", account=IBAN_NL, bic="ABNANL2A"),
                       remittance_unstructured=("Invoice 4711",)),
                   _tx("50.00", DB, swift_tx_type="NMSC")])],
    "C02": [_stmt("SYNTH-C02",
                  _bal(C, 2026, 1, 2, "EUR", "500.00"), _bal(C, 2026, 1, 4, "EUR", "620.00"),
                  [_tx("100.00", C), _tx("80.00", C), _tx("40.00", C), _tx("100.00", DB, swift_tx_type="NDDT")],
                  summary=TransactionsSummary(total_count=4, credit_count=3, credit_sum=D("220.00"),
                                              debit_count=1, debit_sum=D("100.00"),
                                              net_amount=D("120.00"), net_credit_debit=C))],
    "C03": [_stmt("SYNTH-C03",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "300.00"),
                  [_tx("200.00", C, end_to_end_id="E2E-C03",
                       remittance_unstructured=("Rechnung 2026-77 Teil 1", "Teil 2 Lieferung 9"),
                       creditor_reference="RF18539007547034")])],
    "C04": [_stmt("SYNTH-C04",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "110.00"),
                  [_tx("10.00", C)],
                  closing_available=_bal(C, 2026, 1, 3, "EUR", "105.00"),
                  forward_available=(_bal(C, 2026, 1, 4, "EUR", "110.00"),),
                  other_balances=(("PRCD", _bal(C, 2026, 1, 1, "EUR", "100.00")),
                                  ("ITBD", _bal(C, 2026, 1, 2, "EUR", "104.00"))))],
    "C06": [_stmt("SYNTH-C06",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "175.00"),
                  [_tx("50.00", C)])],  # declared closing off by 25 → FAIL_RECONCILIATION
    "C07": [_stmt("SYNTH-C07",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "115.00"),
                  [_tx("20.00", C, is_reversal=True), _tx("5.00", DB, is_reversal=True)])],
    "C08": [_stmt("SYNTH-C08",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "230.00"),
                  [_tx("130.00", C, entry_reference="BATCH-C08",
                       details=(_tx("100.00", C, end_to_end_id="E2E-A"),
                                _tx("30.00", C, end_to_end_id="E2E-B")))])],
    "C09": [_stmt("SYNTH-C09",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "110.00"),
                  [_tx("10.00", C), _tx("55.00", DB, status=EntryStatus.PDNG)])],
    "C11": [_stmt("SYNTH-C11",
                  _bal(C, 2026, 1, 2, "EUR", "100.00"), _bal(C, 2026, 1, 3, "EUR", "110.00"),
                  [_tx("10.00", C),
                   _tx("25.00", DB, currency="USD", instructed_amount=D("27.30"),
                       instructed_currency="USD", exchange_rate=D("1.092"))])],
    "C12": [_stmt("SYNTH-C12",
                  _bal(C, 2026, 1, 2, "EUR", "42.00"), _bal(C, 2026, 1, 2, "EUR", "42.00"), [])],
    "C14": [Statement(statement_id="SYNTH-C14", account_iban=IBAN, account_currency="EUR",
                      opening_balance=_bal(C, 2026, 1, 2, "EUR", "10.00"),
                      closing_balance=_bal(C, 2026, 1, 2, "EUR", "10.00"),
                      source_format="synthetic")],
}

CAMT_EXPECT: dict[str, dict] = {
    "C01": dict(tx=2, opening="1000.00", credits="200.00", debits="50.00", closing="1150.00", ok=True, warns=[]),
    "C02": dict(tx=4, opening="500.00", credits="220.00", debits="100.00", closing="620.00", ok=True, warns=[]),
    "C03": dict(tx=1, opening="100.00", credits="200.00", debits="0", closing="300.00", ok=True, warns=[]),
    "C04": dict(tx=1, opening="100.00", credits="10.00", debits="0", closing="110.00", ok=True, warns=[]),
    "C06": dict(tx=1, opening="100.00", credits="50.00", debits="0", closing="175.00", ok=False, warns=[]),
    "C07": dict(tx=2, opening="100.00", credits="20.00", debits="5.00", closing="115.00", ok=True, warns=[]),
    "C08": dict(tx=1, opening="100.00", credits="130.00", debits="0", closing="230.00", ok=True, warns=[]),
    "C09": dict(tx=1, opening="100.00", credits="10.00", debits="0", closing="110.00", ok=True, warns=["W_NON_BOOKED_ENTRY"]),
    "C11": dict(tx=1, opening="100.00", credits="10.00", debits="0", closing="110.00", ok=True, warns=["W_ENTRY_CURRENCY_DIFFERS"]),
    "C12": dict(tx=0, opening="42.00", credits="0", debits="0", closing="42.00", ok=True, warns=[]),
    "C14": dict(tx=0, opening="10.00", credits="0", debits="0", closing="10.00", ok=True, warns=[]),
}

C05_INVALID = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>SYNTH-C05</MsgId><CreDtTm>2026-01-15T10:30:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>SYNTH-C05</Id>
      <CreDtTm>2026-01-15T10:30:00</CreDtTm>
      <Acct><Id><IBAN>DE75512108001245126199</IBAN></Id><Ccy>EUR</Ccy></Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="EUR">100.00</Amt>
        <Dt><Dt>2026-01-02</Dt></Dt>
      </Bal>
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""  # missing mandatory CdtDbtInd in Bal, missing CLBD → schema-invalid

C10_INTRST_WRAP = "<Intrst><Tp><Cd>INDY</Cd></Tp></Intrst>"

C13_UNSUPPORTED = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.05">
  <BkToCstmrStmt><GrpHdr><MsgId>SYNTH-C13</MsgId></GrpHdr></BkToCstmrStmt>
</Document>
"""


def build_camt_fixtures() -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for cid, statements in CAMT_MODELS.items():
        payload, _ = write_camt053(statements, V02, CLOCK)
        out[cid] = payload
    # C10: schema-valid file containing an element the model does not carry (Intrst)
    base = out["C12"].decode("utf-8")
    assert "<TxsSummry>" not in base
    c10 = base.replace("<Ntry>", "", 1)  # no entries in C12 anyway
    c10 = c10.replace("</Acct>", "</Acct>")  # no-op, keep structure clear
    # insert statement-level Intrst after the last Bal
    idx = c10.rindex("</Bal>") + len("</Bal>")
    c10 = c10[:idx] + C10_INTRST_WRAP + c10[idx:]
    c10 = c10.replace("SYNTH-C12", "SYNTH-C10")
    out["C10"] = c10.encode("utf-8")
    out["C05"] = C05_INVALID.encode("utf-8")
    out["C13"] = C13_UNSUPPORTED.encode("utf-8")
    return out


# --------------------------------------------------------------------------
# CSV fixtures
# --------------------------------------------------------------------------

def build_csv_fixtures(camt_bytes: dict[str, bytes]) -> dict[str, tuple[bytes, bytes]]:
    out: dict[str, tuple[bytes, bytes]] = {}
    # V01: canonical pair exported from the M01-equivalent model (C01 statements)
    tx, st, _ = write_csv(CAMT_MODELS["C01"])
    out["V01"] = (tx, st)
    # V02: formula-injection payloads in text fields
    s = _stmt("SYNTH-V02", _bal(C, 2026, 1, 2, "EUR", "10.00"),
              _bal(C, 2026, 1, 3, "EUR", "30.00"),
              [_tx("20.00", C, remittance_unstructured=("=cmd|' /C calc'!A0",),
                   counterparty=Counterparty(name="@SUM(A1:A9)"),
                   customer_reference="+1+2")])
    tx, st, _ = write_csv(s.__class__ and [s])
    out["V02"] = (tx, st)
    # V03: quoted fields, embedded commas and newline, BOM handling
    s = _stmt("SYNTH-V03", _bal(C, 2026, 1, 2, "EUR", "10.00"),
              _bal(C, 2026, 1, 3, "EUR", "25.00"),
              [_tx("15.00", C,
                   remittance_unstructured=('He said "pay, now"', "second, line"),
                   counterparty=Counterparty(name="Example, Jane"))])
    tx, st, _ = write_csv([s])
    out["V03"] = (tx, st)
    # V04: missing required column (drop value_date from the V01 header)
    tx01, st01 = out["V01"]
    text = tx01.decode("utf-8-sig").replace("value_date", "not_value_date", 1)
    out["V04"] = (b"\xef\xbb\xbf" + text.encode("utf-8"), st01)
    # V05: bad amount + bad date values
    text = tx01.decode("utf-8-sig").replace("2026-01-03", "01/03/2026").replace("200.00", "2OO.OO")
    out["V05"] = (b"\xef\xbb\xbf" + text.encode("utf-8"), st01)
    return out


# --------------------------------------------------------------------------
# Golden case freezing
# --------------------------------------------------------------------------

def _check_expect(sid: str, statements, expect: dict) -> list:
    recons = [reconcile_statement(s) for s in statements]
    total_tx = sum(r.transaction_count for r in recons)
    assert total_tx == expect["tx"], f"{sid}: tx {total_tx} != {expect['tx']}"
    r = recons[0]
    assert r.opening_declared == D(expect["opening"]), f"{sid}: opening {r.opening_declared}"
    assert sum((x.total_credits for x in recons), D(0)) == D(expect["credits"]), f"{sid}: credits"
    assert sum((x.total_debits for x in recons), D(0)) == D(expect["debits"]), f"{sid}: debits"
    assert recons[-1].closing_declared == D(expect["closing"]), f"{sid}: closing"
    assert all(x.passed for x in recons) == expect["ok"], f"{sid}: passed mismatch"
    return recons


def freeze_case(case_id: str, input_rel: str, source_format: str,
                payload: ConversionInput, expect: dict | None,
                error_code: str | None, targets: list[str],
                extra_warns: list[str] | None = None) -> None:
    case_dir = GOLDEN / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    expected_dir = case_dir / "expected"
    expected_dir.mkdir(exist_ok=True)
    manifest: dict = {
        "id": case_id,
        "input": {"file": input_rel, "format": source_format, "provenance": "SYNTHETIC"},
        "conversions": [],
    }
    if error_code:
        try:
            read_input(source_format, payload)
        except Exception as exc:  # noqa: BLE001 - generation-time verification
            actual = getattr(exc, "code", type(exc).__name__)
            assert actual == error_code, f"{case_id}: raised {actual}, authored {error_code}"
        else:
            raise AssertionError(f"{case_id}: expected {error_code} but input parsed successfully")
        manifest["validation"] = {"expected_result": "FAIL_PARSE", "expected_errors": [error_code]}
        (case_dir / "case.json").write_text(json.dumps(manifest, indent=2), "utf-8")
        return

    statements, read_report = read_input(source_format, payload)
    if read_report.has_errors:
        manifest["validation"] = {
            "expected_result": "FAIL_SCHEMA",
            "expected_errors": sorted({d.code for d in read_report.errors}),
        }
        (case_dir / "case.json").write_text(json.dumps(manifest, indent=2), "utf-8")
        return

    assert expect is not None
    recons = _check_expect(case_id, statements, expect)
    (expected_dir / "normalized.json").write_text(
        json.dumps([statement_to_dict(s) for s in statements], indent=2, sort_keys=True),
        "utf-8")
    r = recons[0]
    manifest["reconciliation"] = {
        "currency": expect["ccy"] if "ccy" in expect else statements[0].account_currency,
        "opening_balance": str(r.opening_declared),
        "closing_balance": str(recons[-1].closing_declared),
        "total_credits": str(sum((x.total_credits for x in recons), D(0))),
        "total_debits": str(sum((x.total_debits for x in recons), D(0))),
        "transaction_count": sum(x.transaction_count for x in recons),
        "credit_count": sum(x.credit_count for x in recons),
        "debit_count": sum(x.debit_count for x in recons),
    }
    manifest["validation"] = {
        "expected_result": "PASS" if expect["ok"] else "FAIL_RECONCILIATION",
        "expected_warnings": expect["warns"] + (extra_warns or []),
    }

    diag_codes: dict[str, list[str]] = {}
    loss_by_target: dict[str, list] = {}
    for target in targets:
        result = convert(source_format, target, payload, CLOCK)
        assert result.conservation_verified, f"{case_id}->{target}"
        suffix = {"mt940": "sta", "camt.053.001.02": "xml", "camt.053.001.08": "xml",
                  "csv": "csv", "xlsx": "xlsx"}[target]
        name = f"output.{target}.{suffix}"
        if target == "csv":
            (expected_dir / f"output.{target}.transactions.csv").write_bytes(
                result.output.csv_transactions)
            (expected_dir / f"output.{target}.statements.csv").write_bytes(
                result.output.csv_statements)
            files = [f"output.{target}.transactions.csv", f"output.{target}.statements.csv"]
        else:
            (expected_dir / name).write_bytes(result.output.primary())
            files = [name]
        manifest["conversions"].append({"target": target, "expected_output": files})
        diag_codes[target] = sorted({d.code for d in result.report.diagnostics})
        loss_by_target[target] = sorted(
            {(n.field_name, n.kind.value, n.direction) for n in result.report.loss_notes})
    (expected_dir / "diagnostics.json").write_text(
        json.dumps({"codes": diag_codes,
                    "loss": {k: [list(x) for x in v] for k, v in loss_by_target.items()}},
                   indent=2, sort_keys=True), "utf-8")
    (case_dir / "case.json").write_text(json.dumps(manifest, indent=2), "utf-8")


def main() -> int:
    for sub in ("mt940", "camt053", "csv"):
        d = FIXTURES / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    if GOLDEN.exists():
        shutil.rmtree(GOLDEN)
    GOLDEN.mkdir(parents=True)

    for mid, content in MT940_FIXTURES.items():
        (FIXTURES / "mt940" / f"{mid}.sta").write_bytes(content.encode("utf-8"))
    camt_bytes = build_camt_fixtures()
    for cid, payload in camt_bytes.items():
        (FIXTURES / "camt053" / f"{cid}.xml").write_bytes(payload)
    csv_pairs = build_csv_fixtures(camt_bytes)
    for vid, (tx, st) in csv_pairs.items():
        (FIXTURES / "csv" / f"{vid}.transactions.csv").write_bytes(tx)
        (FIXTURES / "csv" / f"{vid}.statements.csv").write_bytes(st)

    # ---- golden cases ----
    for mid, content in MT940_FIXTURES.items():
        payload = ConversionInput(data=content.encode("utf-8"))
        expect = MT940_EXPECT.get(mid)
        error = MT940_ERRORS.get(mid)
        targets = []
        if expect and expect["ok"]:
            targets = [FORMAT_CAMT_V02, FORMAT_CSV]
            if mid in ("M01", "M13"):
                targets.append(FORMAT_CAMT_V08)
            if mid == "M01":
                targets.append("xlsx")
        elif expect:
            targets = [FORMAT_CSV]  # reconciliation failures still convert; camt optional
        if mid == "M19":
            targets = [FORMAT_CSV]  # M19 recon fails (declared mismatch by design of big JPY sums)
        freeze_case(f"G-{mid}", f"tests/fixtures/mt940/{mid}.sta", FORMAT_MT940,
                    payload, expect, error, targets)

    for cid, payload_bytes in camt_bytes.items():
        payload = ConversionInput(data=payload_bytes)
        expect = CAMT_EXPECT.get(cid)
        error = "E_CAMT_UNSUPPORTED_VERSION" if cid == "C13" else None
        targets = []
        if expect and expect["ok"]:
            targets = [FORMAT_MT940, FORMAT_CSV]
            if cid == "C01":
                targets.append(FORMAT_CAMT_V08)
        elif expect:
            targets = [FORMAT_CSV]
        if cid == "C11":
            targets = [FORMAT_CSV]  # MT940 refused (foreign-currency entry)
        freeze_case(f"G-{cid}", f"tests/fixtures/camt053/{cid}.xml", FORMAT_CAMT_V02,
                    payload, expect, error, targets)

    # CSV round-trip goldens (V06 role): V01 → mt940 and camt
    tx, st = csv_pairs["V01"]
    freeze_case("G-V01", "tests/fixtures/csv/V01.transactions.csv", FORMAT_CSV,
                ConversionInput(csv_transactions=tx, csv_statements=st),
                dict(tx=2, opening="1000.00", credits="200.00", debits="50.00",
                     closing="1150.00", ok=True, warns=[]),
                None, [FORMAT_MT940, FORMAT_CAMT_V02])
    print(f"fixtures: {len(MT940_FIXTURES)} mt940, {len(camt_bytes)} camt, {len(csv_pairs)} csv pairs")
    print(f"golden cases: {len(list(GOLDEN.iterdir()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
