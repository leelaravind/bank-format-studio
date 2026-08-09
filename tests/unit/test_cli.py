"""P1-M8 CLI tests: validate/convert commands drive the full core pipeline."""

from pathlib import Path

from bfs_cli.main import main

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def test_validate_ok():
    assert main(["validate", str(FIXTURES / "mt940" / "M01.sta")]) == 0


def test_validate_reconciliation_failure_exit_1(capsys):
    assert main(["validate", str(FIXTURES / "mt940" / "M11.sta")]) == 1
    out = capsys.readouterr()
    assert "E_RECON_MISMATCH" in out.err or "E_RECON_MISMATCH" in out.out


def test_validate_hard_error_exit_2(capsys):
    assert main(["validate", str(FIXTURES / "mt940" / "M09.sta")]) == 2
    assert "E_MT940_MISSING_CLOSING" in capsys.readouterr().err


def test_convert_mt940_to_camt(tmp_path):
    out = tmp_path / "out.xml"
    code = main(["convert", str(FIXTURES / "mt940" / "M01.sta"),
                 "--to", "camt.053.001.02", "--out", str(out)])
    assert code == 0
    payload = out.read_bytes()
    assert b"camt.053.001.02" in payload and b"SYNTH-M01" in payload


def test_convert_to_csv_writes_pair(tmp_path):
    out = tmp_path / "result.transactions.csv"
    code = main(["convert", str(FIXTURES / "mt940" / "M01.sta"),
                 "--to", "csv", "--out", str(out)])
    assert code == 0
    assert out.exists()
    assert (tmp_path / "result.statements.csv").exists()


def test_convert_csv_pair_to_mt940(tmp_path):
    out = tmp_path / "roundtrip.sta"
    code = main(["convert", str(FIXTURES / "csv" / "V01.transactions.csv"),
                 "--to", "mt940", "--out", str(out), "--format", "csv"])
    assert code == 0
    assert out.read_bytes().startswith(b":20:")
