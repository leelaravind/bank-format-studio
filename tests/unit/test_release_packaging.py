"""Release packaging checks (Step 2): EULA presence and sync, installer wiring,
publisher/product identity, third-party notices untouched."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EULA_MD = ROOT / "docs" / "EULA.md"
EULA_TXT = ROOT / "packaging" / "EULA.txt"
ISS = (ROOT / "packaging" / "installer.iss").read_text("utf-8")
SPEC = (ROOT / "packaging" / "bfs.spec").read_text("utf-8")


def _normalized(text: str) -> str:
    """Formatting-insensitive fingerprint: same words in the same order."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _collapsed(text: str) -> str:
    """Whitespace-collapsed text so hard line wraps don't break phrase checks."""
    return " ".join(text.split())


def test_eula_files_exist_and_are_synchronized():
    assert EULA_MD.is_file() and EULA_TXT.is_file()
    assert _normalized(EULA_MD.read_text("utf-8")) == _normalized(EULA_TXT.read_text("utf-8"))


def test_eula_release_placeholders_still_open():
    # [RELEASE DATE] / support contact are owner-supplied at release time and
    # must never be silently invented.
    for path in (EULA_MD, EULA_TXT):
        text = path.read_text("utf-8")
        assert "[RELEASE DATE]" in text
        assert "[INSERT SUPPORT EMAIL OR SUPPORT URL]" in text


def test_eula_carries_locked_licence_model():
    text = _collapsed(EULA_TXT.read_text("utf-8"))
    for term in (
        "Leela Aravind Karlapudi",
        "ITISYOU",
        "Bank Statement Format Studio",
        "licensed, not sold",
        "one-time purchase",
        "non-exclusive, non-transferable",
        "one (1) licensed user",
        "three (3) devices",
        "commercial or business use",
        "There is no subscription",
        "locally on your device",
        "banking, accounting, tax, legal or financial advice",
        "England and Wales",
    ):
        assert term in text, f"EULA.txt missing locked term: {term!r}"


def test_eula_does_not_override_third_party_licences():
    text = _collapsed(EULA_TXT.read_text("utf-8"))
    assert "THIRD-PARTY-NOTICES.txt" in text
    assert "Nothing in this EULA restricts, overrides or limits any rights" in text


def test_installer_presents_eula_and_ships_it():
    assert "LicenseFile=EULA.txt" in ISS
    assert 'Source: "EULA.txt"; DestDir: "{app}"' in ISS
    assert "EULA.txt" in SPEC  # bundled in the onedir dist as well


def test_installer_identity_is_set():
    assert '#define AppPublisher "Leela Aravind Karlapudi"' in ISS
    assert "OWNER-LEGAL-ENTITY-NAME" not in ISS
    version_info = (ROOT / "packaging" / "version_info.txt").read_text("utf-8")
    assert "Leela Aravind Karlapudi" in version_info
    assert "Bank Statement Format Studio" in version_info
    assert 'version=str(ROOT / "packaging" / "version_info.txt")' in SPEC


def test_third_party_notices_remain_shipped():
    assert 'Source: "THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"' in ISS
    assert 'Source: "licenses\\*"; DestDir: "{app}\\licenses"' in ISS
    assert "THIRD-PARTY-NOTICES.txt" in SPEC
    for name in ("LICENSE.LGPL3.txt", "LICENSE.GPL3.txt"):
        assert (ROOT / "packaging" / "licenses" / name).is_file()
