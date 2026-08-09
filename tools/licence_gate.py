"""Dependency licence gate (SEC-20, LICENCE-AUDIT policy: zero GPL/AGPL in the build).

Checks every installed distribution in the current environment against an
allowlist of permissive licences and an explicit blocklist of copyleft licences.
Exit code 0 = pass, 1 = violation found.

Usage:
    python tools/licence_gate.py            # audit current environment
    python tools/licence_gate.py --self-test  # prove the gate fails on GPL input
"""

from __future__ import annotations

import argparse
import sys
from importlib import metadata

ALLOWED_SUBSTRINGS = (
    "mit",
    "bsd",
    "apache",
    "python software foundation",
    "psf",
    "isc",
    "zlib",
    "mpl-2.0",  # file-level copyleft, acceptable unmodified; flagged in notices
    "historical permission",
    "unlicense",
    "cc0",
)
BLOCKED_SUBSTRINGS = (
    "agpl",
    "affero",
    "gpl",  # matches GPL and LGPL; LGPL requires an explicit exception entry
)
# Explicit exceptions: distribution name (lower) -> reason recorded in the audit.
EXCEPTIONS = {
    # LGPL-3.0 used dynamically per docs/PACKAGING-STACK-RESEARCH.md compliance checklist.
    "pyside6": "LGPL-3.0 dynamic linking, approved with conditions (LICENCE-AUDIT.md §2)",
    "pyside6-essentials": "LGPL-3.0 dynamic linking, approved with conditions",
    "pyside6-addons": "LGPL-3.0 dynamic linking, approved with conditions",
    "shiboken6": "LGPL-3.0 dynamic linking, approved with conditions",
    # Build tool only, never shipped as a library; bootloader exception applies.
    "pyinstaller": "GPL-2.0+ with Bootloader Exception, build-time only",
    "pyinstaller-hooks-contrib": "GPL-2.0+ with same exception, build-time only",
}
# First-party code — the product itself, not a third-party dependency.
FIRST_PARTY = {"bank-format-studio"}
# Dev/test-only tools excluded from the shipped-product audit (never bundled).
DEV_ONLY = {"pip", "setuptools", "wheel", "pytest", "pluggy", "iniconfig", "colorama",
            "packaging", "ruff", "pip-licenses", "prettytable", "wcwidth", "pygments",
            "pip-tools", "build", "pyproject-hooks", "click", "tomli"}


def licence_of(dist: metadata.Distribution) -> str:
    md = dist.metadata
    lic = (md.get("License-Expression") or md.get("License") or "").strip()
    if not lic or lic.upper() == "UNKNOWN" or len(lic) > 120:
        classifiers = [v for k, v in md.items() if k == "Classifier" and v.startswith("License ::")]
        if classifiers:
            lic = "; ".join(c.split("::")[-1].strip() for c in classifiers)
    return lic


def check(entries: list[tuple[str, str]]) -> list[str]:
    """entries: (distribution name, licence string). Returns violation messages."""
    violations = []
    for name, lic in entries:
        # PyPI distribution names normalize - and _ interchangeably.
        lname, llic = name.lower().replace("_", "-"), lic.lower()
        if lname in DEV_ONLY or lname in FIRST_PARTY:
            continue
        if lname in EXCEPTIONS:
            continue
        if any(b in llic for b in BLOCKED_SUBSTRINGS):
            violations.append(f"BLOCKED licence for {name}: {lic!r}")
            continue
        if not llic:
            violations.append(f"UNKNOWN licence for {name}: metadata empty — investigate before shipping")
            continue
        if not any(a in llic for a in ALLOWED_SUBSTRINGS):
            violations.append(f"UNRECOGNIZED licence for {name}: {lic!r} — not on allowlist")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true",
                        help="prove the gate rejects GPL/AGPL/unknown entries")
    args = parser.parse_args()

    if args.self_test:
        planted = [("evil-gpl-lib", "GPL-3.0-only"), ("evil-agpl-lib", "AGPL-3.0"),
                   ("mystery-lib", ""), ("good-lib", "MIT")]
        v = check(planted)
        ok = len(v) == 3 and not any("good-lib" in m for m in v)
        print("\n".join(v))
        print(f"self-test {'PASSED' if ok else 'FAILED'}: gate rejected {len(v)}/3 planted entries")
        return 0 if ok else 1

    entries = [(d.metadata["Name"] or "?", licence_of(d)) for d in metadata.distributions()]
    violations = check(entries)
    if violations:
        print("LICENCE GATE FAILED:")
        print("\n".join(f"  {m}" for m in violations))
        return 1
    audited = [e for e in entries if e[0].lower() not in DEV_ONLY]
    print(f"licence gate passed: {len(audited)} shipped-candidate distributions audited")
    for name, lic in sorted(audited):
        print(f"  {name}: {lic}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
