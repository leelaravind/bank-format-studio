"""Bank Statement Format Studio — PySide6 desktop GUI.

Thin by design: every parse/convert/reconcile operation is a bfs_core call.
Workflow: Open → detect/validate → preview → choose target → convert →
reconciliation & information-loss results → Save.

Privacy posture (docs/SECURITY-REQUIREMENTS.md): fully offline, no telemetry,
statement data only in memory, nothing written until the user saves.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bfs_core import __version__
from bfs_core.convert import (
    WRITABLE_FORMATS,
    ConversionInput,
    ConversionResult,
    convert,
    detect_format,
    read_input,
)
from bfs_core.errors import BfsError
from bfs_core.model import Severity, Statement
from bfs_core.reconcile import reconcile_statement
from bfs_core.security import resolve_inside, sanitize_filename, sweep_leftovers

ABOUT_TEXT = f"""<h3>Bank Statement Format Studio {__version__}</h3>
<p>Offline converter for MT940, ISO 20022 camt.053 (.001.02/.001.08), CSV and Excel.</p>
<p>All processing happens locally on this computer. No bank data ever leaves
this machine; the application makes no network connections.</p>
<p>This application uses the Qt framework via PySide6 under the GNU LGPL v3.
See THIRD-PARTY-NOTICES.txt in the installation folder for all third-party
licences and for instructions on obtaining the Qt source code.</p>
<p>&copy; 2026 Leela Aravind Karlapudi. All rights reserved.</p>"""


# Explicit Windows AppUserModelID: without it the taskbar may attribute the
# window to a generic host identity instead of this product (and pinned/
# grouped taskbar entries then show the wrong icon).
APP_USER_MODEL_ID = "ITISYOU.BankStatementFormatStudio.1"


def app_icon() -> QIcon:
    """Product icon for the runtime Qt surfaces (title bar, taskbar, Alt-Tab).

    The icon embedded in the PE resources of BankFormatStudio.exe only covers
    Explorer/shortcut surfaces; Qt paints its own window icon and falls back
    to a generic one unless it is set explicitly. Resolve the .ico that
    PyInstaller ships inside the frozen bundle (sys._MEIPASS, the _internal
    directory in onedir builds) — never a repository-relative path — and fall
    back to the repo copy only for source checkouts.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2] / "packaging"
    return QIcon(str(base / "logo.ico"))


class _WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class _Worker(QRunnable):
    def __init__(self, fn, *args):
        super().__init__()
        self.fn, self.args = fn, args
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        try:
            self.signals.finished.emit(self.fn(*self.args))
        except Exception as exc:  # noqa: BLE001 - surfaced to the user dialog
            self.signals.failed.emit(exc)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Bank Statement Format Studio")
        self.setWindowIcon(app_icon())
        self.resize(1080, 720)
        self.pool = QThreadPool.globalInstance()
        self.source_format: str | None = None
        self.payload: ConversionInput | None = None
        self.statements: list[Statement] = []
        self.result: ConversionResult | None = None
        self._build_ui()
        sweep_leftovers()  # SEC-07 crash-leftover sweep at startup

    # ---------------- UI scaffolding ----------------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.open_button = QPushButton("Open statement…")
        self.open_button.clicked.connect(self.open_file)
        toolbar.addWidget(self.open_button)
        self.file_label = QLabel("No file open")
        self.file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        toolbar.addWidget(self.file_label, stretch=1)
        toolbar.addWidget(QLabel("Convert to:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(list(WRITABLE_FORMATS))
        toolbar.addWidget(self.target_combo)
        self.convert_button = QPushButton("Convert")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.run_conversion)
        toolbar.addWidget(self.convert_button)
        self.save_button = QPushButton("Save output…")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_output)
        toolbar.addWidget(self.save_button)
        about = QPushButton("About")
        about.clicked.connect(lambda: QMessageBox.about(self, "About", ABOUT_TEXT))
        toolbar.addWidget(about)
        layout.addLayout(toolbar)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        self.tabs = QTabWidget()
        self.preview = QTableWidget()
        self.preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabs.addTab(self.preview, "Transactions")
        self.report_view = QPlainTextEdit()
        self.report_view.setReadOnly(True)
        self.tabs.addTab(self.report_view, "Validation && reconciliation")
        self.loss_view = QPlainTextEdit()
        self.loss_view.setReadOnly(True)
        self.tabs.addTab(self.loss_view, "Information loss")
        layout.addWidget(self.tabs, stretch=1)

        self.setCentralWidget(central)

    # ---------------- Open / validate ----------------

    def open_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open bank statement", "",
            "Bank statements (*.sta *.mt940 *.940 *.txt *.xml *.csv);;All files (*)")
        if not path_str:
            return
        path = Path(path_str)
        try:
            data = path.read_bytes()
            fmt = detect_format(data)
            if fmt == "csv":
                payload = self._csv_payload(path, data)
                if payload is None:
                    return
            else:
                payload = ConversionInput(data=data)
        except OSError as exc:
            QMessageBox.critical(self, "Cannot open file", str(exc))
            return
        self._set_busy(True, "Reading…")
        worker = _Worker(read_input, fmt, payload)
        worker.signals.finished.connect(
            lambda res, f=fmt, p=payload, name=path.name: self._loaded(f, p, name, res))
        worker.signals.failed.connect(self._load_failed)
        self.pool.start(worker)

    def _csv_payload(self, path: Path, data: bytes) -> ConversionInput | None:
        candidate = Path(str(path).replace("transactions", "statements"))
        if candidate != path and candidate.exists():
            return ConversionInput(csv_transactions=data,
                                   csv_statements=candidate.read_bytes())
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Select the matching statements.csv", str(path.parent), "CSV (*.csv)")
        if not chosen:
            return None
        return ConversionInput(csv_transactions=data,
                               csv_statements=Path(chosen).read_bytes())

    def _loaded(self, fmt: str, payload: ConversionInput, name: str, result) -> None:
        statements, report = result
        self._set_busy(False)
        self.source_format = fmt
        self.payload = payload
        self.statements = statements
        self.result = None
        self.save_button.setEnabled(False)
        self.file_label.setText(f"{name} — detected {fmt}")
        recons = [reconcile_statement(s) for s in statements]
        self._render_report(report, recons)
        self._render_preview(statements)
        self.loss_view.setPlainText("")
        if report.has_errors:
            self.summary_label.setText("⚠ The file failed validation — see the report tab.")
            self.convert_button.setEnabled(False)
        else:
            total = sum(len(s.transactions) for s in statements)
            ok = all(r.passed for r in recons)
            self.summary_label.setText(
                f"{len(statements)} statement(s), {total} transactions — "
                + ("balances reconcile ✓" if ok else "⚠ BALANCES DO NOT RECONCILE"))
            self.convert_button.setEnabled(True)

    def _load_failed(self, exc: Exception) -> None:
        self._set_busy(False)
        self.convert_button.setEnabled(False)
        if isinstance(exc, BfsError):
            QMessageBox.critical(self, "Cannot read this file",
                                 f"{exc}\n\nDiagnostic code: {exc.code}")
        else:
            QMessageBox.critical(self, "Unexpected error", str(exc))

    # ---------------- Convert / save ----------------

    def run_conversion(self) -> None:
        if not self.payload or not self.source_format:
            return
        target = self.target_combo.currentText()
        self._set_busy(True, "Converting…")
        worker = _Worker(convert, self.source_format, target, self.payload,
                         datetime.now(timezone.utc))
        worker.signals.finished.connect(self._converted)
        worker.signals.failed.connect(self._load_failed)
        self.pool.start(worker)

    def _converted(self, result: ConversionResult) -> None:
        self._set_busy(False)
        self.result = result
        self._render_report(result.report, result.reconciliations)
        self._render_loss(result)
        ok = result.reconciliation_passed and not result.report.has_errors
        self.summary_label.setText(
            f"Converted to {result.target_format} — "
            + ("reconciliation preserved ✓" if ok else "⚠ completed with findings, see report")
            + (f"; {len(result.report.loss_notes)} information-loss note(s)"
               if result.report.loss_notes else "; no information loss recorded"))
        self.save_button.setEnabled(result.output.data is not None
                                    or result.output.csv_transactions is not None)
        self.tabs.setCurrentWidget(self.loss_view if result.report.loss_notes else self.report_view)

    def save_output(self) -> None:
        if not self.result:
            return
        target = self.result.target_format
        suffix = {"mt940": ".sta", "camt.053.001.02": ".xml",
                  "camt.053.001.08": ".xml", "csv": ".csv", "xlsx": ".xlsx"}[target]
        base = sanitize_filename(self.statements[0].statement_id if self.statements else "statement")
        suggested = f"{base}.{target}{suffix}" if target != "csv" else f"{base}.transactions.csv"
        path_str, _ = QFileDialog.getSaveFileName(self, "Save converted output", suggested)
        if not path_str:
            return
        chosen = Path(path_str)
        try:
            safe = resolve_inside(chosen.parent, sanitize_filename(chosen.name))
            if target == "csv":
                safe.write_bytes(self.result.output.csv_transactions)
                st_name = safe.name.replace("transactions", "statements") \
                    if "transactions" in safe.name else f"statements-{safe.name}"
                st_path = resolve_inside(chosen.parent, st_name)
                st_path.write_bytes(self.result.output.csv_statements)
                QMessageBox.information(self, "Saved",
                                        f"Saved:\n{safe}\n{st_path}\n\n"
                                        "(statements.csv accompanies every CSV export)")
            else:
                safe.write_bytes(self.result.output.primary())
                QMessageBox.information(self, "Saved", f"Saved:\n{safe}")
        except (OSError, BfsError) as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    # ---------------- Rendering ----------------

    def _render_preview(self, statements: list[Statement]) -> None:
        columns = ["Statement", "Value date", "Booking date", "Amount", "C/D",
                   "Reversal", "Type", "Counterparty", "Reference", "Remittance"]
        rows = [
            (s.statement_id, t.value_date.isoformat(),
             t.booking_date.isoformat() if t.booking_date else "",
             f"{t.signed()} {t.currency or s.account_currency}",
             t.credit_debit.value, "yes" if t.is_reversal else "",
             t.swift_tx_type or (t.btc.proprietary if t.btc and t.btc.proprietary else ""),
             (t.counterparty.name or t.counterparty.account or "") if t.counterparty else "",
             t.customer_reference or t.end_to_end_id or "",
             " ".join(t.remittance_unstructured))
            for s in statements for t in s.transactions
        ]
        self.preview.setColumnCount(len(columns))
        self.preview.setHorizontalHeaderLabels(columns)
        self.preview.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.preview.setItem(r, c, QTableWidgetItem(str(value)))
        self.preview.resizeColumnsToContents()

    def _render_report(self, report, recons) -> None:
        lines = []
        for r in recons:
            status = "RECONCILED" if r.passed else "MISMATCH"
            lines.append(f"[{status}] opening {r.opening_declared} {r.currency} | "
                         f"credits {r.total_credits} | debits {r.total_debits} | "
                         f"closing declared {r.closing_declared} / computed {r.closing_computed} | "
                         f"{r.transaction_count} transactions")
        for d in report.diagnostics:
            lines.append(f"[{d.severity.value.upper()}] {d.message}  ({d.code})")
        for r in recons:
            for d in r.report.diagnostics:
                if d.severity is not Severity.ERROR:  # errors already shown via report merge
                    lines.append(f"[{d.severity.value.upper()}] {d.message}  ({d.code})")
        self.report_view.setPlainText("\n".join(lines) or "No findings.")

    def _render_loss(self, result: ConversionResult) -> None:
        if not result.report.loss_notes:
            self.loss_view.setPlainText(
                "No information loss recorded for this conversion.")
            return
        lines = [
            "This conversion changed or dropped the following information "
            "(the formats are not equally expressive):", ""]
        lines += [f"• {n.field_name} — {n.kind.value} ({n.direction})"
                  f"{': ' + n.detail if n.detail else ''}"
                  + (f"  [{n.location}]" if n.location else "")
                  for n in result.report.loss_notes]
        self.loss_view.setPlainText("\n".join(lines))

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self.open_button.setEnabled(not busy)
        self.convert_button.setEnabled(not busy and bool(self.statements))
        if busy:
            self.summary_label.setText(text)


def main() -> int:
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    app = QApplication(sys.argv)
    app.setApplicationName("Bank Statement Format Studio")
    app.setOrganizationName("Leela Aravind Karlapudi")
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
