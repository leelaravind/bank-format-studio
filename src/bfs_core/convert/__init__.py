"""Conversion engine and BTC mapping data."""

from bfs_core.convert.btc_map import btc_to_swift, swift_to_btc
from bfs_core.convert.engine import (
    FORMAT_CAMT_V02,
    FORMAT_CAMT_V08,
    FORMAT_CSV,
    FORMAT_MT940,
    FORMAT_XLSX,
    READABLE_FORMATS,
    WRITABLE_FORMATS,
    ConversionInput,
    ConversionOutput,
    ConversionResult,
    convert,
    detect_format,
    read_input,
)

__all__ = [
    "FORMAT_CAMT_V02",
    "FORMAT_CAMT_V08",
    "FORMAT_CSV",
    "FORMAT_MT940",
    "FORMAT_XLSX",
    "READABLE_FORMATS",
    "WRITABLE_FORMATS",
    "ConversionInput",
    "ConversionOutput",
    "ConversionResult",
    "btc_to_swift",
    "convert",
    "detect_format",
    "read_input",
    "swift_to_btc",
]
