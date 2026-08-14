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


def test_eula_release_values_filled():
    # Owner-supplied release values (V1 freeze, Step 6): the placeholders are
    # resolved and must not reappear.
    for path in (EULA_MD, EULA_TXT):
        text = path.read_text("utf-8")
        assert "[RELEASE DATE]" not in text
        assert "[INSERT SUPPORT EMAIL OR SUPPORT URL]" not in text
        assert "10 August 2026" in text
        assert text.count("support@itisyou.app") == 2


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


def test_product_icon_ico_exists_with_required_sizes():
    ico = ROOT / "packaging" / "logo.ico"
    assert ico.is_file()
    data = ico.read_bytes()
    import struct

    reserved, ico_type, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, ico_type) == (0, 1)  # valid .ico header
    sizes = set()
    for i in range(count):
        w, h = struct.unpack_from("<BB", data, 6 + i * 16)
        sizes.add((w or 256, h or 256))  # 0 encodes 256 in ICONDIRENTRY
    required = {(s, s) for s in (16, 32, 48, 64, 128, 256)}
    assert required <= sizes, f"missing sizes: {required - sizes}"


def test_product_icon_is_wired_into_spec_and_installer():
    assert 'icon=str(ROOT / "packaging" / "logo.ico")' in SPEC
    assert "icon=None" not in SPEC
    assert "SetupIconFile=logo.ico" in ISS
    assert r"UninstallDisplayIcon={app}\BankFormatStudio.exe" in ISS


def test_runtime_qt_icon_is_wired_and_ico_ships_in_the_bundle():
    # RC defect regression: the PE-embedded icon covers Explorer only; the
    # running window needs an explicit Qt icon loaded from the frozen bundle.
    main_src = (ROOT / "src" / "bfs_app" / "main.py").read_text("utf-8")
    assert "setWindowIcon" in main_src
    assert "logo.ico" in main_src
    assert "_MEIPASS" in main_src  # frozen-bundle resolution, not repo-relative
    assert "SetCurrentProcessExplicitAppUserModelID" in main_src
    assert '(str(ROOT / "packaging" / "logo.ico"), ".")' in SPEC


def _bmp_size(path: Path) -> tuple[int, int]:
    import struct

    data = path.read_bytes()
    assert data[:2] == b"BM", f"{path.name} is not a BMP (Inno requires BMP)"
    width, height = struct.unpack_from("<ii", data, 18)
    return width, abs(height)


def test_installer_wizard_branding_images_exist_and_are_wired():
    # Owner-visible installer branding: corner logo on every wizard page and
    # the welcome/finish banner (SetupIconFile alone shows nothing in the UI).
    expected = {
        "wizard-small.bmp": (55, 55),
        "wizard-small-2x.bmp": (110, 110),
        "wizard-image.bmp": (164, 314),
        "wizard-image-2x.bmp": (328, 628),
    }
    for name, size in expected.items():
        assert _bmp_size(ROOT / "packaging" / name) == size, f"{name} has wrong dimensions"
    assert "WizardSmallImageFile=wizard-small.bmp,wizard-small-2x.bmp" in ISS
    assert "WizardImageFile=wizard-image.bmp,wizard-image-2x.bmp" in ISS


def test_original_logo_source_unchanged():
    # assets/logo/logo.png is the untouched source/reference asset; the icon
    # pipeline (tools/make_icon.py) must only ever read it.
    import hashlib

    digest = hashlib.sha256((ROOT / "assets" / "logo" / "logo.png").read_bytes()).hexdigest()
    assert digest == "553a58250586031bda576b8cb411c0d9bf7d36b5eb940a909d383a193ca6b98e"
    assert (ROOT / "assets" / "logo" / "app-icon-master.png").is_file()


def test_third_party_notices_remain_shipped():
    assert 'Source: "THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"' in ISS
    assert 'Source: "licenses\\*"; DestDir: "{app}\\licenses"' in ISS
    assert "THIRD-PARTY-NOTICES.txt" in SPEC
    for name in ("LICENSE.LGPL3.txt", "LICENSE.GPL3.txt"):
        assert (ROOT / "packaging" / "licenses" / name).is_file()
