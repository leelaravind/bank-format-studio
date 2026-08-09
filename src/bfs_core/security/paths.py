"""Output-path safety (SEC-08): sanitize derived filenames, contain writes.

Filenames derived from statement data (IDs, accounts) are untrusted input.
"""

from __future__ import annotations

import re
from pathlib import Path

from bfs_core.errors import E_INTERNAL, W_FILENAME_SANITIZED, BfsError
from bfs_core.model import DiagnosticReport

_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10)),
    "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
}
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def sanitize_filename(name: str, report: DiagnosticReport | None = None,
                      fallback: str = "statement") -> str:
    """Make an arbitrary string safe as a single Windows/POSIX filename component."""
    original = name
    cleaned = _BAD_CHARS.sub("_", name)
    cleaned = cleaned.replace("..", "_")
    cleaned = cleaned.strip().rstrip(". ")
    stem = cleaned.split(".")[0].upper()
    if stem in _RESERVED:
        cleaned = f"_{cleaned}"
    if not cleaned:
        cleaned = fallback
    cleaned = cleaned[:120]
    if cleaned != original and report is not None:
        report.warning(W_FILENAME_SANITIZED, value=original, detail=cleaned)
    return cleaned


def resolve_inside(base_dir: Path, filename: str) -> Path:
    """Join base_dir with an already-sanitized filename and verify the final
    resolved path stays inside base_dir (defence in depth)."""
    base = base_dir.resolve()
    target = (base / filename).resolve()
    if base != target and base not in target.parents:
        raise BfsError(E_INTERNAL,
                       detail=f"resolved output path {target} escapes chosen directory {base}")
    return target
