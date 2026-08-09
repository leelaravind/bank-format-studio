# PyInstaller spec — Bank Statement Format Studio (--onedir, Windows-first).
# onedir is a locked decision: it satisfies the LGPL relink obligation (Qt DLLs
# replaceable on disk) and avoids the --onefile AV heuristics.
# Build:  pyinstaller packaging/bfs.spec --noconfirm --distpath packaging/dist

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH injected by PyInstaller

a = Analysis(
    [str(ROOT / "src" / "bfs_app" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "src" / "bfs_core" / "camt" / "schemas" / "camt.053.001.02.xsd"),
         "bfs_core/camt/schemas"),
        (str(ROOT / "src" / "bfs_core" / "camt" / "schemas" / "camt.053.001.08.xsd"),
         "bfs_core/camt/schemas"),
        (str(ROOT / "src" / "bfs_core" / "convert" / "data" / "btc_map.json"),
         "bfs_core/convert/data"),
        (str(ROOT / "packaging" / "THIRD-PARTY-NOTICES.txt"), "."),
    ],
    hiddenimports=[],
    excludes=[
        # Trim unused Qt modules and heavyweight stdlib extras.
        "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf",
        "PySide6.QtOpenGL", "PySide6.QtDBus", "PySide6.QtTest", "PySide6.QtSql",
        "PySide6.QtWebEngineCore", "PySide6.QtMultimedia", "PySide6.Qt3DCore",
        "tkinter", "unittest", "pydoc",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BankFormatStudio",
    console=False,
    icon=None,  # OWNER ACTION: product icon asset
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=False,  # locked decision: UPX raises AV false positives
    name="BankFormatStudio",
)
