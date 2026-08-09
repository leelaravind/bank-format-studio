"""Golden-case runner (P1-M6): input → normalized model → outputs → reconciliation
→ diagnostics, byte-exact against the frozen expectations.

Covers INV-7 (conservation asserted inside the engine on every conversion) and
INV-8 (round-trip conservation via the CSV/MT940/camt golden chains).
"""

import io
import json
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from bfs_core.convert import ConversionInput, convert, read_input
from bfs_core.errors import BfsError
from bfs_core.model import statement_to_dict
from bfs_core.reconcile import reconcile_statement

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "golden-cases"
CLOCK = datetime(2026, 1, 15, 10, 30)

CASES = sorted(p.name for p in GOLDEN.iterdir() if (p / "case.json").exists())


def _outputs_equal(name: str, produced: bytes, expected: bytes) -> bool:
    """Byte-exact for every format; xlsx falls back to member-wise equality.

    The xlsx container's deflate streams differ between zlib builds (CPython
    3.14 ships zlib-ng; 3.12/3.13 classic zlib), so the frozen container bytes
    are only reproducible on the build that froze them. Member names, order and
    uncompressed member bytes must still match exactly — content determinism is
    fully asserted; only the compression encoding may vary.
    """
    if produced == expected:
        return True
    if not name.endswith(".xlsx"):
        return False
    za = zipfile.ZipFile(io.BytesIO(produced))
    zb = zipfile.ZipFile(io.BytesIO(expected))
    return za.namelist() == zb.namelist() and all(
        za.read(n) == zb.read(n) for n in za.namelist()
    )


def _payload(manifest: dict) -> ConversionInput:
    input_file = ROOT / manifest["input"]["file"]
    if manifest["input"]["format"] == "csv":
        statements_file = Path(str(input_file).replace("transactions.csv", "statements.csv"))
        return ConversionInput(csv_transactions=input_file.read_bytes(),
                               csv_statements=statements_file.read_bytes())
    return ConversionInput(data=input_file.read_bytes())


@pytest.mark.golden
@pytest.mark.parametrize("case_id", CASES)
def test_golden_case(case_id):
    case_dir = GOLDEN / case_id
    manifest = json.loads((case_dir / "case.json").read_text("utf-8"))
    source_format = manifest["input"]["format"]
    payload = _payload(manifest)
    validation = manifest.get("validation", {})
    expected_result = validation.get("expected_result", "PASS")

    if expected_result == "FAIL_PARSE":
        with pytest.raises(BfsError) as excinfo:
            read_input(source_format, payload)
        assert excinfo.value.code in validation["expected_errors"], excinfo.value
        return

    statements, report = read_input(source_format, payload)

    if expected_result == "FAIL_SCHEMA":
        assert report.has_errors
        assert {d.code for d in report.errors} <= set(validation["expected_errors"]) or \
               {d.code for d in report.errors} == set(validation["expected_errors"])
        return

    # Normalized model must match the frozen expectation exactly.
    expected_model = json.loads((case_dir / "expected" / "normalized.json").read_text("utf-8"))
    assert [statement_to_dict(s) for s in statements] == expected_model

    # Reconciliation figures must match the authored manifest values.
    recons = [reconcile_statement(s) for s in statements]
    figures = manifest["reconciliation"]
    assert recons[0].opening_declared == Decimal(figures["opening_balance"])
    assert recons[-1].closing_declared == Decimal(figures["closing_balance"])
    assert sum((r.total_credits for r in recons), Decimal(0)) == Decimal(figures["total_credits"])
    assert sum((r.total_debits for r in recons), Decimal(0)) == Decimal(figures["total_debits"])
    assert sum(r.transaction_count for r in recons) == figures["transaction_count"]
    if expected_result == "PASS":
        assert all(r.passed for r in recons), [d.message for r in recons for d in r.report.errors]
    else:
        assert expected_result == "FAIL_RECONCILIATION"
        assert not all(r.passed for r in recons)

    # Expected warnings must be present (asserted, not just tolerated).
    all_codes = set(report.codes()) | {c for r in recons for c in r.report.codes()}
    for warning in validation.get("expected_warnings", []):
        assert warning in all_codes, f"expected {warning} in {sorted(all_codes)}"

    # Conversions: byte-exact outputs + diagnostics parity.
    diagnostics = json.loads((case_dir / "expected" / "diagnostics.json").read_text("utf-8")) \
        if (case_dir / "expected" / "diagnostics.json").exists() else {"codes": {}, "loss": {}}
    for conversion in manifest.get("conversions", []):
        target = conversion["target"]
        result = convert(source_format, target, payload, CLOCK)
        assert result.conservation_verified  # INV-7
        produced = {}
        if target == "csv":
            produced[f"output.{target}.transactions.csv"] = result.output.csv_transactions
            produced[f"output.{target}.statements.csv"] = result.output.csv_statements
        else:
            produced[conversion["expected_output"][0]] = result.output.primary()
        for name in conversion["expected_output"]:
            expected_bytes = (case_dir / "expected" / name).read_bytes()
            assert _outputs_equal(name, produced[name], expected_bytes), \
                f"{case_id}:{name} differs from frozen output"
        assert sorted({d.code for d in result.report.diagnostics}) == diagnostics["codes"][target]
        got_loss = sorted([n.field_name, n.kind.value, n.direction]
                          for n in {(x.field_name, x.kind, x.direction): x
                                    for x in result.report.loss_notes}.values())
        expected_loss = sorted(diagnostics["loss"][target])
        assert got_loss == expected_loss, f"{case_id}:{target} loss notes differ"


@pytest.mark.golden
def test_round_trip_inv8_mt940_camt_mt940():
    """INV-8: MT940 → camt.053.001.02 → MT940 conserves all reconciliation figures."""
    data = (ROOT / "tests" / "fixtures" / "mt940" / "M01.sta").read_bytes()
    first = convert("mt940", "camt.053.001.02", ConversionInput(data=data), CLOCK)
    second = convert("camt.053.001.02", "mt940",
                     ConversionInput(data=first.output.primary()), CLOCK)
    keys_in = [reconcile_statement(s).conservation_key() for s in first.statements]
    keys_out = [reconcile_statement(s).conservation_key() for s in second.statements]
    assert keys_in == keys_out


@pytest.mark.golden
def test_round_trip_inv8_camt_mt940_camt():
    data = (ROOT / "tests" / "fixtures" / "camt053" / "C01.xml").read_bytes()
    first = convert("camt.053.001.02", "mt940", ConversionInput(data=data), CLOCK)
    second = convert("mt940", "camt.053.001.02",
                     ConversionInput(data=first.output.primary()), CLOCK)
    keys_in = [reconcile_statement(s).conservation_key() for s in first.statements]
    keys_out = [reconcile_statement(s).conservation_key() for s in second.statements]
    assert keys_in == keys_out
    # Field-level: the structured references survive the round trip.
    t_in = first.statements[0].transactions[0]
    t_out = second.statements[0].transactions[0]
    assert t_in.end_to_end_id == t_out.end_to_end_id == "E2E-C01-1"
    assert t_out.counterparty and t_out.counterparty.name == "Acme Tooling GmbH"
