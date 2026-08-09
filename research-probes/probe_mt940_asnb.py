"""RESEARCH PROBE (disposable). Verifies mt-940's bank-variant mechanism:
the ASNB fixture requires the library's StatementASNB tag implementation,
and per-statement (not per-file) reconciliation of a multi-statement file.
"""
import decimal
import pathlib

import mt940
from mt940.tags import StatementASNB

SAMPLES = pathlib.Path(__file__).resolve().parent.parent / "sample-data" / "public" / "mt940"

# 1. ASNB variant via custom statement tag
tag_parser = StatementASNB()
ts = mt940.models.Transactions(tags={tag_parser.id: tag_parser})
ts.parse((SAMPLES / "wolph-mt940-asnb.txt").read_text())
print(f"ASNB with StatementASNB: parsed OK, {len(ts)} transactions")

# 2. Per-statement reconciliation on a multi-statement file (abnamro)
raw = (SAMPLES / "wolph-mt940-jejik-abnamro.sta").read_text()
# jejik abnamro file: statements separated by '-' line
ok = 0
for chunk in [c for c in raw.split("\n-\n") if ":20:" in c]:
    t = mt940.models.Transactions()
    t.parse(chunk)
    d = t.data
    ob = d.get("final_opening_balance")
    cb = d.get("final_closing_balance")
    if ob and cb:
        total = sum((x.data["amount"].amount for x in t), decimal.Decimal(0))
        delta = cb.amount.amount - ob.amount.amount
        print(f"  stmt {d.get('transaction_reference')}: sum {total} vs delta {delta}"
              f" -> {'RECONCILES' if total == delta else 'MISMATCH'}")
        ok += total == delta
print(f"per-statement reconciliation passes: {ok}")
