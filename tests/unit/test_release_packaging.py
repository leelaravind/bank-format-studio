"""Release packaging checks: EULA presence and sync, installer wiring,
publisher/product identity, third-party notices untouched, and the
unsigned-release (£0) path — formalized, mitigated, never faked."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EULA_MD = ROOT / "docs" / "EULA.md"
EULA_TXT = ROOT / "packaging" / "EULA.txt"
ISS = (ROOT / "packaging" / "installer.iss").read_text("utf-8")
SPEC = (ROOT / "packaging" / "bfs.spec").read_text("utf-8")
BUILD = (ROOT / "packaging" / "build.ps1").read_text("utf-8")
POLICY = ROOT / "docs" / "UNSIGNED-RELEASE-POLICY.md"


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


def test_unsigned_release_policy_exists_and_is_honest():
    text = _collapsed(POLICY.read_text("utf-8"))
    assert "without Authenticode code signing" in text
    # Mandatory £0 mitigations:
    assert "SHA256SUMS.txt" in text
    assert "two independent channels" in text.lower()
    assert "VirusTotal" in text
    # Honesty constraints stay written down:
    assert "never presented as signed" in text
    assert "No self-signed Authenticode certificates" in text
    assert "Never instruct users to disable or weaken SmartScreen" in text
    # Disclosure snippet for the download page is present:
    assert "This installer is not code-signed" in text


def test_unsigned_policy_is_wired_into_requirements_and_checklist():
    sec = (ROOT / "docs" / "SECURITY-REQUIREMENTS.md").read_text("utf-8")
    checklist = (ROOT / "docs" / "RELEASE-CHECKLIST.md").read_text("utf-8")
    readme = (ROOT / "README.md").read_text("utf-8")
    assert "UNSIGNED-RELEASE-POLICY" in sec  # SEC-19 amended, not contradicted
    assert "UNSIGNED-RELEASE-POLICY" in checklist
    assert "UNSIGNED-RELEASE-POLICY" in readme
    # The superseded absolute rule must be gone, its replacement present:
    assert "Never released unsigned" not in checklist
    assert "never presented as signed" in _collapsed(checklist)


def test_build_generates_checksum_manifest_and_stays_unsigned():
    assert "SHA256SUMS.txt" in BUILD
    assert "Get-FileHash" in BUILD and "SHA256" in BUILD
    # The build must keep saying so, and must not invoke a signing tool:
    assert "UNSIGNED" in BUILD
    for line in BUILD.splitlines():
        code = line.split("#", 1)[0].lower()
        assert "signtool" not in code, f"signing invoked without a certificate: {line!r}"


def test_installer_signing_hook_is_inert_not_faked():
    for line in ISS.splitlines():
        stripped = line.strip()
        if stripped.startswith(";"):
            continue
        assert not stripped.lower().startswith("signtool"), (
            f"active SignTool directive without a certificate: {line!r}"
        )
    assert "UNSIGNED-RELEASE-POLICY" in ISS


def test_third_party_notices_remain_shipped():
    assert 'Source: "THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"' in ISS
    assert 'Source: "licenses\\*"; DestDir: "{app}\\licenses"' in ISS
    assert "THIRD-PARTY-NOTICES.txt" in SPEC
    for name in ("LICENSE.LGPL3.txt", "LICENSE.GPL3.txt"):
        assert (ROOT / "packaging" / "licenses" / name).is_file()
