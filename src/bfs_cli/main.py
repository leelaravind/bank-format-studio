"""Internal CLI for tests, CI and support — not a marketed product surface.

Commands:
  bfs validate <file> [--format FMT]
  bfs convert <file> --to FMT --out PATH [--format FMT] [--statements-csv PATH]

Exit codes: 0 ok, 1 validation/reconciliation errors, 2 hard failure.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from bfs_core.convert import (
    READABLE_FORMATS,
    WRITABLE_FORMATS,
    ConversionInput,
    convert,
    detect_format,
    read_input,
)
from bfs_core.errors import BfsError
from bfs_core.model import Severity
from bfs_core.reconcile import reconcile_statement
from bfs_core.security import resolve_inside, sanitize_filename


def _load(path: Path, fmt: str | None, statements_csv: Path | None) -> tuple[str, ConversionInput]:
    data = path.read_bytes()
    fmt = fmt or detect_format(data)
    if fmt == "csv":
        st_path = statements_csv or Path(str(path).replace("transactions", "statements"))
        return fmt, ConversionInput(csv_transactions=data, csv_statements=st_path.read_bytes())
    return fmt, ConversionInput(data=data)


def _print_report(report, recons=None) -> None:
    for d in report.diagnostics:
        stream = sys.stderr if d.severity is Severity.ERROR else sys.stdout
        print(f"[{d.severity.value.upper()}] {d.code}: {d.message}", file=stream)
    for n in report.loss_notes:
        print(f"[LOSS] {n.field_name} ({n.kind.value}, {n.direction}): {n.detail}")
    for r in recons or []:
        status = "RECONCILED" if r.passed else "MISMATCH"
        print(f"[{status}] opening {r.opening_declared} {r.currency}, "
              f"credits {r.total_credits}, debits {r.total_debits}, "
              f"closing declared {r.closing_declared} / computed {r.closing_computed}, "
              f"{r.transaction_count} transactions")


def cmd_validate(args: argparse.Namespace) -> int:
    fmt, payload = _load(Path(args.file), args.format, None)
    statements, report = read_input(fmt, payload)
    recons = [reconcile_statement(s) for s in statements]
    for r in recons:
        report.extend(r.report)
    _print_report(report, recons)
    print(f"format: {fmt}; statements: {len(statements)}")
    return 0 if not report.has_errors and all(r.passed for r in recons) else 1


def cmd_convert(args: argparse.Namespace) -> int:
    fmt, payload = _load(Path(args.file), args.format,
                         Path(args.statements_csv) if args.statements_csv else None)
    result = convert(fmt, args.to, payload, datetime.now(timezone.utc))
    _print_report(result.report, result.reconciliations)
    if result.output.data is None and result.output.csv_transactions is None:
        return 1  # input had validation errors; nothing was produced
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(out.name)
    target = resolve_inside(out.parent, safe_name)
    if args.to == "csv":
        target.write_bytes(result.output.csv_transactions)
        st_target = resolve_inside(out.parent, safe_name.replace("transactions", "statements")
                                   if "transactions" in safe_name else f"statements-{safe_name}")
        st_target.write_bytes(result.output.csv_statements)
        print(f"wrote {target} and {st_target}")
    else:
        target.write_bytes(result.output.primary())
        print(f"wrote {target}")
    return 0 if result.reconciliation_passed and not result.report.has_errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bfs", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="parse, XSD-validate and reconcile a file")
    p_validate.add_argument("file")
    p_validate.add_argument("--format", choices=READABLE_FORMATS)
    p_validate.set_defaults(func=cmd_validate)

    p_convert = sub.add_parser("convert", help="convert a file to another format")
    p_convert.add_argument("file")
    p_convert.add_argument("--to", required=True, choices=WRITABLE_FORMATS)
    p_convert.add_argument("--out", required=True)
    p_convert.add_argument("--format", choices=READABLE_FORMATS)
    p_convert.add_argument("--statements-csv")
    p_convert.set_defaults(func=cmd_convert)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BfsError as exc:
        print(f"[ERROR] {exc.code}: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"[ERROR] file access failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
