"""Runtime Qt icon wiring (regression for the V1 RC title-bar defect).

The icon embedded in BankFormatStudio.exe's PE resources only covers
Explorer/shortcut surfaces; the running window's title bar, taskbar entry and
Alt-Tab tile use the Qt window icon, which must be set explicitly at runtime
from the .ico shipped inside the PyInstaller bundle.

These tests pin that wiring (icon set, correct artwork, frozen-bundle path
resolution). They are AUTOMATED RESOURCE VERIFICATION only — the actual
on-screen title-bar/taskbar appearance still requires manual visual
verification on a real Windows session.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.gui

ROOT = Path(__file__).resolve().parents[2]
ICO = ROOT / "packaging" / "logo.ico"


def test_app_icon_loads_the_product_ico(qapp):
    from bfs_app.main import app_icon

    icon = app_icon()
    assert not icon.isNull()
    sizes = {(s.width(), s.height()) for s in icon.availableSizes()}
    # Small (title bar) and large (Alt-Tab/taskbar) frames must both exist.
    assert {(16, 16), (32, 32), (256, 256)} <= sizes


def test_main_window_title_bar_icon_is_set_and_matches_product_icon(qtbot):
    from PySide6.QtGui import QIcon

    from bfs_app.main import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    assert not window.windowIcon().isNull(), "window icon missing - generic icon regression"
    got = window.windowIcon().pixmap(32, 32).toImage()
    expected = QIcon(str(ICO)).pixmap(32, 32).toImage()
    assert not got.isNull()
    assert got == expected, "window icon is not the packaged product icon"


def test_app_icon_resolves_inside_frozen_bundle(qapp, tmp_path, monkeypatch):
    # PyInstaller onedir: sys.frozen is set and sys._MEIPASS points at
    # _internal, where bfs.spec ships logo.ico.
    from bfs_app import main as app_main

    bundle = tmp_path / "_internal"
    bundle.mkdir()
    shutil.copy2(ICO, bundle / "logo.ico")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    icon = app_main.app_icon()
    assert icon.availableSizes(), "frozen app_icon() did not load the bundled logo.ico"


def test_app_icon_frozen_never_falls_back_to_repository_paths(qapp, tmp_path, monkeypatch):
    # An empty bundle must yield an empty icon: proves the frozen path uses
    # only the bundle, so the fix cannot silently depend on the checkout.
    from bfs_app import main as app_main

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(empty), raising=False)
    assert app_main.app_icon().availableSizes() == []


def test_windows_app_user_model_id_is_product_specific():
    from bfs_app.main import APP_USER_MODEL_ID

    assert APP_USER_MODEL_ID.startswith("ITISYOU.")
    assert "BankStatementFormatStudio" in APP_USER_MODEL_ID
