"""camt.053 reading and validation (writers added in P1-M5)."""

from bfs_core.camt.reader import read_camt053
from bfs_core.camt.versions import V02, V08, VersionSpec, detect_version

__all__ = ["V02", "V08", "VersionSpec", "detect_version", "read_camt053"]
