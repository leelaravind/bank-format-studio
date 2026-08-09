# Bank Statement Format Studio

An offline Windows desktop utility that converts and validates bank statement
formats — **MT940 ↔ ISO 20022 camt.053 (.001.02 / .001.08) ↔ CSV**, plus Excel
(XLSX) export — with official-XSD validation, balance reconciliation and an
explicit information-loss report on every conversion. All processing is local;
no bank data ever leaves the machine and the application makes no network
connections.

Version 1.0.0 · proprietary/commercial · source code private.
Publisher: Leela Aravind Karlapudi · © 2026 Leela Aravind Karlapudi.

## Repository layout

```
src/bfs_core/     conversion/domain library (pure, offline)
src/bfs_app/      PySide6 desktop GUI
src/bfs_cli/      internal CLI (CI/support)
tests/            unit + golden + security + GUI suites, synthetic fixtures
packaging/        PyInstaller spec, Inno Setup installer, notices, build script
docs/             customer CSV dialect, security requirements, research records
spec/             locked V1 specifications and implementation plan
references/       ISO 20022 schemas + licence texts (provenance in docs/)
```

## Development

Canonical build interpreter: **Python 3.14 (64-bit, Windows)**; runtime floor 3.12.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,gui,build]"
.venv\Scripts\python.exe -m pytest tests          # full suite (warnings are errors)
.venv\Scripts\python.exe -m ruff check src tests tools
.venv\Scripts\python.exe tools\licence_gate.py    # dependency licence audit
```

Runtime dependencies are hash-pinned in `requirements.lock`; dev/build tooling
in `requirements-build.lock`. Fixtures and golden cases are regenerated
deterministically by `tools\gen_fixtures.py` — never edit frozen goldens by hand.

## Windows build

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

Produces `packaging/dist/BankFormatStudio/` (onedir) and, with Inno Setup 6
installed, `packaging/Output/BankFormatStudio-<version>-setup.exe`. Release
binaries must be code-signed before distribution (owner action; see
`docs/RELEASE-CHECKLIST.md`).
