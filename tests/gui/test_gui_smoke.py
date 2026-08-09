"""P1-M8 GUI smoke tests (pytest-qt, offscreen platform).

The GUI is thin; these tests verify the open→preview→convert→report wiring
against bfs_core, not visual appearance.
"""

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bfs_core.convert import ConversionInput, read_input  # noqa: E402

pytestmark = pytest.mark.gui

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture
def window(qtbot):
    from bfs_app.main import MainWindow
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def _load(window, qtbot, fixture: str):
    data = (FIXTURES / "mt940" / fixture).read_bytes()
    payload = ConversionInput(data=data)
    result = read_input("mt940", payload)
    window._loaded("mt940", payload, fixture, result)


def test_open_renders_preview_and_summary(window, qtbot):
    _load(window, qtbot, "M01.sta")
    assert window.preview.rowCount() == 2
    assert "reconcile ✓" in window.summary_label.text()
    assert window.convert_button.isEnabled()


def test_reconciliation_failure_flagged(window, qtbot):
    _load(window, qtbot, "M11.sta")
    assert "DO NOT RECONCILE" in window.summary_label.text()
    assert "MISMATCH" in window.report_view.toPlainText()


def test_convert_and_loss_report(window, qtbot):
    _load(window, qtbot, "M01.sta")
    window.target_combo.setCurrentText("camt.053.001.02")
    window.run_conversion()
    qtbot.waitUntil(lambda: window.result is not None, timeout=15000)
    assert window.save_button.isEnabled()
    assert "Converted to camt.053.001.02" in window.summary_label.text()


def test_clipboard_untouched_by_conversion(window, qtbot):
    # SEC-24: conversion flow never writes to the clipboard.
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setText("sentinel")
    _load(window, qtbot, "M01.sta")
    window.target_combo.setCurrentText("csv")
    window.run_conversion()
    qtbot.waitUntil(lambda: window.result is not None, timeout=15000)
    assert QApplication.clipboard().text() == "sentinel"
