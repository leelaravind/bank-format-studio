"""Temporary-file lifecycle (SEC-07).

The core pipeline works in memory and needs no temp files; this module exists for
the GUI/packaging layers (e.g. staged saves) so any temp usage is uniform:
unpredictable names, owner-only access where the OS supports it, deterministic
cleanup, best-effort overwrite before delete, and a startup sweep for crash
leftovers.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import tempfile
from pathlib import Path

_PREFIX = "bfs-"
_SUBDIR = "bank-format-studio"


def _temp_root() -> Path:
    root = Path(tempfile.gettempdir()) / _SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_temp_file(suffix: str = ".tmp") -> Path:
    """Create an empty temp file with an unpredictable name, owner-restricted."""
    root = _temp_root()
    name = f"{_PREFIX}{secrets.token_hex(16)}{suffix}"
    path = root / name
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    return path


def secure_delete(path: Path) -> None:
    """Best-effort overwrite-then-delete (documented as best-effort: SEC-23
    honesty — the OS may have paged or journaled content elsewhere)."""
    with contextlib.suppress(OSError):
        if path.is_file():
            size = path.stat().st_size
            if 0 < size <= 64 * 1024 * 1024:
                with open(path, "r+b") as handle:
                    handle.write(b"\x00" * size)
                    handle.flush()
                    os.fsync(handle.fileno())
        path.unlink(missing_ok=True)


def sweep_leftovers() -> int:
    """Startup sweep (SEC-07): delete any temp files a previous crash left behind.
    Returns the number of files removed."""
    removed = 0
    root = _temp_root()
    for path in root.glob(f"{_PREFIX}*"):
        secure_delete(path)
        removed += 1
    return removed


@contextlib.contextmanager
def temp_file(suffix: str = ".tmp"):
    path = create_temp_file(suffix)
    try:
        yield path
    finally:
        secure_delete(path)
