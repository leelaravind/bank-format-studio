"""Input resource limits (SEC-14). Central so every reader enforces the same caps."""

from __future__ import annotations

from dataclasses import dataclass

from bfs_core.errors import E_INPUT_TOO_LARGE, BfsError


@dataclass(frozen=True)
class Limits:
    max_input_bytes: int = 64 * 1024 * 1024        # 64 MiB per input file
    max_line_chars: int = 32 * 1024                # one physical MT940/CSV line
    max_transactions: int = 500_000                # entries per file
    max_xml_depth: int = 64
    max_xlsx_uncompressed: int = 256 * 1024 * 1024
    max_xlsx_ratio: int = 200                      # compression-ratio bomb threshold

    def check_size(self, n_bytes: int, what: str = "input file") -> None:
        if n_bytes > self.max_input_bytes:
            raise BfsError(E_INPUT_TOO_LARGE,
                           detail=f"{what} is {n_bytes} bytes; limit {self.max_input_bytes}")

    def check_line(self, n_chars: int, where: str) -> None:
        if n_chars > self.max_line_chars:
            raise BfsError(E_INPUT_TOO_LARGE,
                           detail=f"line at {where} is {n_chars} characters; limit {self.max_line_chars}")

    def check_count(self, n: int, what: str = "transactions") -> None:
        if n > self.max_transactions:
            raise BfsError(E_INPUT_TOO_LARGE,
                           detail=f"{n} {what}; limit {self.max_transactions}")


DEFAULT_LIMITS = Limits()
