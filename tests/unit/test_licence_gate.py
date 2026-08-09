"""T-SEC-20 (partial): licence gate logic rejects copyleft and unknown licences."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import licence_gate  # noqa: E402


def test_gate_blocks_gpl_agpl_and_unknown():
    entries = [
        ("evil-gpl-lib", "GPL-3.0-only"),
        ("evil-agpl-lib", "GNU Affero General Public License v3"),
        ("mystery-lib", ""),
        ("weird-lib", "Custom Proprietary Licence"),
        ("good-mit", "MIT"),
        ("good-bsd", "BSD-3-Clause"),
        ("good-psf", "Python Software Foundation License"),
    ]
    violations = licence_gate.check(entries)
    flagged = {v.split(" for ")[1].split(":")[0] for v in violations}
    assert flagged == {"evil-gpl-lib", "evil-agpl-lib", "mystery-lib", "weird-lib"}


def test_gate_allows_lgpl_only_via_explicit_exception():
    assert licence_gate.check([("some-lgpl-lib", "LGPL-3.0-only")])
    assert not licence_gate.check([("pyside6-essentials", "LGPL-3.0-only")])


def test_dev_only_tools_excluded():
    assert not licence_gate.check([("pytest", "MIT"), ("pip-licenses", "MIT")])


def test_current_environment_passes():
    entries = [
        (d.metadata["Name"] or "?", licence_gate.licence_of(d))
        for d in __import__("importlib.metadata", fromlist=["distributions"]).distributions()
    ]
    assert licence_gate.check(entries) == []
