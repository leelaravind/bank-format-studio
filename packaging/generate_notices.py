"""Generate THIRD-PARTY-NOTICES.txt for the packaged application.

Collects every shipped distribution's licence metadata + the mandatory
attribution blocks (Qt/LGPL relink instructions, ISO 20022/SWIFT schemas,
fixture corpora). Run inside the build venv before PyInstaller.
"""

from __future__ import annotations

import sys
from datetime import date
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import licence_gate  # noqa: E402

HEADER = f"""BANK STATEMENT FORMAT STUDIO — THIRD-PARTY NOTICES
Generated {date.today().isoformat()}

This product bundles the third-party components listed below. Full licence
texts are included in the 'licenses' folder of this installation.

======================================================================
QT FRAMEWORK / PySide6 — GNU LGPL v3
======================================================================
This application uses the Qt framework via PySide6 under the GNU Lesser
General Public License version 3 (LGPL-3.0). Qt is Copyright (C) The Qt
Company Ltd. and other contributors.

- The Qt libraries are dynamically linked and shipped UNMODIFIED as
  separate DLL files in this installation folder.
- You may replace the Qt libraries with your own builds: substitute the
  Qt6*.dll files (and the PySide6/shiboken6 binaries) in the installation
  directory with compatible versions.
- Source code for the exact Qt version used is available from
  https://download.qt.io/official_releases/qt/ and for PySide6 from
  https://code.qt.io/cgit/pyside/pyside-setup.git/
- The complete LGPL-3.0 and GPL-3.0 licence texts are installed alongside
  this file (LICENSE.LGPL3.txt, LICENSE.GPL3.txt).

======================================================================
ISO 20022 MESSAGE SCHEMAS
======================================================================
This product bundles unmodified ISO 20022 message schemas
(camt.053.001.02.xsd, camt.053.001.08.xsd) © SWIFT / ISO 20022
Registration Authority, used under the SWIFTStandards IPR Policy
End-User License Agreement (royalty-free). The schemas are not sold as
part of this product and remain the property of their rights holders.
https://www.iso20022.org/intellectual-property-rights

======================================================================
PYTHON PACKAGES
======================================================================
"""

FOOTER = """
======================================================================
DEVELOPMENT TEST DATA (not shipped in the application binary)
======================================================================
Development fixtures derive from the BSD-3-Clause mt940 project
(Rick van Hattem), MIT-licensed fixtures by Frank Oxener (Agile Dovadi BV)
and Michael Bumann, Apache-2.0 fixtures by betterplace, and MIT-licensed
genkgo/camt fixtures. Licence texts: references/licences/ in the source
repository.

Python is distributed under the Python Software Foundation License.
PyInstaller (build tool, GPL-2.0+ with Bootloader Exception) is used to
package this application; the exception explicitly permits distributing
the bundled application without restriction.
"""


def main() -> int:
    lines = [HEADER]
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"] or "?"
        lname = name.lower().replace("_", "-")
        if lname in licence_gate.DEV_ONLY or lname in licence_gate.FIRST_PARTY:
            continue
        licence = licence_gate.licence_of(dist)
        lines.append(f"{name} {dist.version} — {licence}")
        for key in ("Home-page", "Project-URL"):
            value = dist.metadata.get(key)
            if value:
                lines.append(f"    {value}")
                break
    lines.append(FOOTER)
    out = ROOT / "packaging" / "THIRD-PARTY-NOTICES.txt"
    out.write_text("\n".join(lines), "utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
