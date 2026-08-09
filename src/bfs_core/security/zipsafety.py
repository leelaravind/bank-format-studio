"""Archive safety checks (SEC-15) for xlsx/zip containers.

V1 core does not import xlsx (export-only), but any future open path MUST go
through check_zip_safety first; the GUI uses it if an xlsx is ever offered for
reading, and the S05 security fixtures exercise it directly.
"""

from __future__ import annotations

import io
import zipfile

from bfs_core.errors import E_XLSX_UNSAFE_ARCHIVE, BfsError
from bfs_core.security.limits import DEFAULT_LIMITS, Limits


def check_zip_safety(data: bytes, limits: Limits = DEFAULT_LIMITS) -> None:
    """Reject zip bombs and archive-traversal member names BEFORE extraction."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
    except zipfile.BadZipFile as exc:
        raise BfsError(E_XLSX_UNSAFE_ARCHIVE, detail="not a valid zip archive") from exc

    total_uncompressed = 0
    for info in infos:
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/") or (len(name) > 1 and name[1] == ":"):
            raise BfsError(E_XLSX_UNSAFE_ARCHIVE,
                           detail=f"archive member name {info.filename!r} attempts path traversal")
        total_uncompressed += info.file_size
        if total_uncompressed > limits.max_xlsx_uncompressed:
            raise BfsError(E_XLSX_UNSAFE_ARCHIVE,
                           detail=f"uncompressed size exceeds {limits.max_xlsx_uncompressed} bytes")
        if info.compress_size > 0 and info.file_size / info.compress_size > limits.max_xlsx_ratio:
            raise BfsError(E_XLSX_UNSAFE_ARCHIVE,
                           detail=f"member {info.filename!r} compression ratio "
                                  f"{info.file_size // max(info.compress_size, 1)}:1 exceeds "
                                  f"{limits.max_xlsx_ratio}:1 (zip bomb heuristic)")
