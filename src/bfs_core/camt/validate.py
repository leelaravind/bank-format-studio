"""Offline XSD validation (SEC-02/SEC-13) with human-translatable errors.

Schemas are bundled package data, loaded once per version. schemaLocation hints in
input files are never honoured — validation always runs against the bundled XSD for
the namespace the document declares.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

import xmlschema

from bfs_core.camt.versions import VersionSpec
from bfs_core.errors import E_CAMT_SCHEMA_INVALID
from bfs_core.model import Diagnostic, DiagnosticReport, Severity


@lru_cache(maxsize=4)
def _schema_for(schema_file: str) -> xmlschema.XMLSchema:
    with resources.as_file(
        resources.files("bfs_core.camt") / "schemas" / schema_file
    ) as path:
        return xmlschema.XMLSchema(str(path))


def validate_bytes(data: bytes, spec: VersionSpec, report: DiagnosticReport,
                   max_errors: int = 50) -> bool:
    """Validate document bytes against the bundled XSD. Appends one diagnostic per
    schema violation (XPath + reason). Returns True when valid."""
    schema = _schema_for(spec.schema_file)
    valid = True
    for i, err in enumerate(schema.iter_errors(data)):
        valid = False
        if i >= max_errors:
            report.diagnostics.append(Diagnostic(
                code=E_CAMT_SCHEMA_INVALID, severity=Severity.ERROR,
                message=f"... further schema errors suppressed after {max_errors}",
                location=""))
            break
        report.error(
            E_CAMT_SCHEMA_INVALID,
            location=err.path or "",
            version=f"camt.053.001.{spec.key}",
            detail=err.reason or str(err),
            where=err.path or "document",
        )
    return valid
