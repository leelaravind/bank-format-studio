"""RESEARCH PROBE (disposable, not product code).

Verifies that the mt-940 library (BSD-3-Clause, v5.0.0) parses the collected
public MT940 fixtures, and reports basic statement facts + a naive balance
reconciliation check where opening/closing balances are present.

Run with the probe venv:
  <scratchpad>/probe-venv/Scripts/python.exe research-probes/probe_mt940_parse.py
"""
import decimal
import pathlib
import sys

import mt940

SAMPLES = pathlib.Path(__file__).resolve().parent.parent / "sample-data" / "public" / "mt940"


def main() -> int:
    failures = 0
    for path in sorted(SAMPLES.iterdir()):
        if path.suffix.lower() not in (".sta", ".txt", ".mt940"):
            continue
        print(f"--- {path.name}")
        try:
            transactions = mt940.parse(str(path))
            data = transactions.data
            n = len(transactions)
            ob = data.get("final_opening_balance") or data.get("opening_balance")
            cb = data.get("final_closing_balance") or data.get("closing_balance")
            print(f"    parsed OK: {n} transactions")
            print(f"    account: {data.get('account_identification')!r}")
            print(f"    opening: {ob}  closing: {cb}")
            if ob is not None and cb is not None and n > 0:
                total = sum(
                    (t.data["amount"].amount for t in transactions),
                    decimal.Decimal(0),
                )
                expected = cb.amount.amount - ob.amount.amount
                status = "RECONCILES" if total == expected else f"MISMATCH (sum {total} vs delta {expected})"
                print(f"    movement sum check: {status}")
        except Exception as exc:  # noqa: BLE001 - probe wants every failure visible
            failures += 1
            print(f"    PARSE FAILED: {type(exc).__name__}: {exc}")
    print(f"\nDone. Failures: {failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
