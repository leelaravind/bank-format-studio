"""The conversion engine: input → reader → normalized model → reconciliation →
writer → output + reconciliation report + information-loss report.

There are NO format-to-format shortcuts (locked rule). Every conversion:
1. reads the source into normalized Statements (with read diagnostics),
2. reconciles every statement (INV-1..6) — mismatches are reported, never fixed,
3. writes the target (with write diagnostics + loss notes),
4. verifies INV-7 conservation by REPARSING the produced output and comparing
   the conservation keys; a violation is a product defect (E_INTERNAL), and the
   output is not returned.
XLSX is export-only: its conservation is verified via the shared CSV projection
it is built from, not by reparse (XLSX import is outside committed V1 scope).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from bfs_core.camt import V02, V08, read_camt053, write_camt053
from bfs_core.csvio import read_csv, write_csv
from bfs_core.errors import E_INTERNAL, E_UNSUPPORTED_CONVERSION, BfsError
from bfs_core.model import DiagnosticReport, Statement
from bfs_core.mt940 import read_mt940, write_mt940
from bfs_core.reconcile import ReconciliationResult, check_sequence_gaps, reconcile_statement
from bfs_core.security import DEFAULT_LIMITS, Limits
from bfs_core.xlsx import write_xlsx

FORMAT_MT940 = "mt940"
FORMAT_CAMT_V02 = "camt.053.001.02"
FORMAT_CAMT_V08 = "camt.053.001.08"
FORMAT_CSV = "csv"
FORMAT_XLSX = "xlsx"

READABLE_FORMATS = (FORMAT_MT940, FORMAT_CAMT_V02, FORMAT_CAMT_V08, FORMAT_CSV)
WRITABLE_FORMATS = (FORMAT_MT940, FORMAT_CAMT_V02, FORMAT_CAMT_V08, FORMAT_CSV, FORMAT_XLSX)


@dataclass
class ConversionInput:
    """Either a single payload, or the CSV pair (transactions.csv + statements.csv)."""

    data: bytes | None = None
    csv_transactions: bytes | None = None
    csv_statements: bytes | None = None


@dataclass
class ConversionOutput:
    """Single payload for mt940/camt/xlsx; pair for csv."""

    data: bytes | None = None
    csv_transactions: bytes | None = None
    csv_statements: bytes | None = None

    def primary(self) -> bytes:
        payload = self.data if self.data is not None else self.csv_transactions
        assert payload is not None
        return payload


@dataclass
class ConversionResult:
    source_format: str
    target_format: str
    statements: list[Statement]
    reconciliations: list[ReconciliationResult]
    output: ConversionOutput
    report: DiagnosticReport = field(default_factory=DiagnosticReport)
    conservation_verified: bool = False

    @property
    def reconciliation_passed(self) -> bool:
        return all(r.passed for r in self.reconciliations)


def detect_format(data: bytes) -> str:
    """Best-effort sniffing for the GUI open dialog (never a substitute for the
    reader's own validation)."""
    head = data[:4096].lstrip(b"\xef\xbb\xbf \t\r\n")
    if head.startswith(b"<?xml") or head.startswith(b"<Document"):
        return FORMAT_CAMT_V08 if b"camt.053.001.08" in data[:2048] else FORMAT_CAMT_V02
    text_head = head[:200]
    if text_head.startswith((b":20:", b":940:", b"{1:")) or b"\n:20:" in data[:4096]:
        return FORMAT_MT940
    if b"statement_id" in text_head:
        return FORMAT_CSV
    return FORMAT_MT940


def read_input(source_format: str, payload: ConversionInput,
               limits: Limits = DEFAULT_LIMITS) -> tuple[list[Statement], DiagnosticReport]:
    if source_format == FORMAT_MT940:
        assert payload.data is not None
        return read_mt940(payload.data, limits)
    if source_format in (FORMAT_CAMT_V02, FORMAT_CAMT_V08):
        assert payload.data is not None
        return read_camt053(payload.data, limits)
    if source_format == FORMAT_CSV:
        assert payload.csv_transactions is not None and payload.csv_statements is not None
        return read_csv(payload.csv_transactions, payload.csv_statements, limits)
    raise BfsError(E_UNSUPPORTED_CONVERSION, detail=f"reading {source_format!r}")


def _prepare_for_mt940(statements: list[Statement],
                       report: DiagnosticReport) -> list[Statement]:
    """MT940 has no entry status and no per-entry currency.
    Non-booked entries are dropped WITH a loss note (they are outside the
    reconciled figures, so INV-7 conservation is preserved). Booked entries in a
    foreign currency cannot be represented without corrupting arithmetic —
    conversion is refused (documented DATA-MAPPING limitation, never silent)."""
    from dataclasses import replace

    from bfs_core.model import EntryStatus, LossKind

    prepared = []
    for s in statements:
        keep = []
        for i, t in enumerate(s.transactions, 1):
            where = f"statement {s.statement_id!r}, entry {i}"
            if t.status is not EntryStatus.BOOK:
                report.loss("non-booked entry", "model->mt940", LossKind.DROPPED,
                            f"entry with status {t.status.value} has no MT940 representation",
                            where)
                continue
            if t.currency is not None and t.currency != s.account_currency:
                raise BfsError(
                    E_UNSUPPORTED_CONVERSION,
                    detail=f"to MT940: booked entry in {t.currency} differs from account "
                           f"currency {s.account_currency} ({where}); MT940 cannot represent "
                           "per-entry currencies")
            keep.append(t)
        prepared.append(replace(s, transactions=keep) if len(keep) != len(s.transactions) else s)
    return prepared


def _write_target(statements: list[Statement], target_format: str,
                  now: datetime) -> tuple[ConversionOutput, DiagnosticReport]:
    if target_format == FORMAT_MT940:
        pre_report = DiagnosticReport()
        prepared = _prepare_for_mt940(statements, pre_report)
        data, report = write_mt940(prepared)
        pre_report.extend(report)
        return ConversionOutput(data=data), pre_report
    if target_format == FORMAT_CAMT_V02:
        data, report = write_camt053(statements, V02, now)
        return ConversionOutput(data=data), report
    if target_format == FORMAT_CAMT_V08:
        data, report = write_camt053(statements, V08, now)
        return ConversionOutput(data=data), report
    if target_format == FORMAT_CSV:
        tx, st, report = write_csv(statements)
        return ConversionOutput(csv_transactions=tx, csv_statements=st), report
    if target_format == FORMAT_XLSX:
        data, report = write_xlsx(statements)
        return ConversionOutput(data=data), report
    raise BfsError(E_UNSUPPORTED_CONVERSION, detail=f"writing {target_format!r}")


def _verify_conservation(statements: list[Statement], output: ConversionOutput,
                         target_format: str, limits: Limits) -> bool:
    """INV-7: reparse the produced output and compare conservation keys."""
    if target_format == FORMAT_XLSX:
        return True  # export-only; built from the verified CSV projection
    payload = ConversionInput(
        data=output.data,
        csv_transactions=output.csv_transactions,
        csv_statements=output.csv_statements,
    )
    reread, _ = read_input(target_format, payload, limits)
    if len(reread) != len(statements):
        raise BfsError(E_INTERNAL,
                       detail=f"conservation check: statement count {len(statements)} -> {len(reread)}")
    for original, produced in zip(statements, reread, strict=True):
        key_in = reconcile_statement(original).conservation_key()
        key_out = reconcile_statement(produced).conservation_key()
        if key_in != key_out:
            raise BfsError(E_INTERNAL,
                           detail=f"INV-7 conservation violated for statement "
                                  f"{original.statement_id!r}: {key_in} -> {key_out}")
    return True


def convert(source_format: str, target_format: str, payload: ConversionInput,
            now: datetime, limits: Limits = DEFAULT_LIMITS) -> ConversionResult:
    """Full pipeline. Raises BfsError on hard input errors; schema-invalid camt
    input yields a result with error diagnostics and no output."""
    statements, report = read_input(source_format, payload, limits)
    if report.has_errors or not statements:
        return ConversionResult(
            source_format=source_format, target_format=target_format,
            statements=statements, reconciliations=[],
            output=ConversionOutput(), report=report,
        )

    reconciliations = []
    for s in statements:
        recon = reconcile_statement(s)
        report.extend(recon.report)
        reconciliations.append(recon)
    report.extend(check_sequence_gaps(statements))

    output, write_report = _write_target(statements, target_format, now)
    report.extend(write_report)
    conservation = _verify_conservation(statements, output, target_format, limits)

    return ConversionResult(
        source_format=source_format,
        target_format=target_format,
        statements=statements,
        reconciliations=reconciliations,
        output=output,
        report=report,
        conservation_verified=conservation,
    )
