"""Diagnostics and information-loss reporting types.

Every heuristic, drop, truncation, transliteration or merge performed anywhere in
the pipeline MUST surface as a Diagnostic or LossNote — silent loss is a defect
(IMPLEMENTATION-PLAN.md §3.3).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from bfs_core.errors import render


class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LossKind(enum.Enum):
    DROPPED = "dropped"
    TRUNCATED = "truncated"
    TRANSLITERATED = "transliterated"
    FLATTENED = "flattened"
    DERIVED = "derived"
    MERGED = "merged"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    location: str = ""

    @classmethod
    def make(cls, code: str, severity: Severity, location: str = "", **params: object) -> "Diagnostic":
        return cls(code=code, severity=severity, message=render(code, **params), location=location)


@dataclass(frozen=True)
class LossNote:
    field_name: str
    direction: str          # e.g. "mt940->camt.053.001.02"
    kind: LossKind
    detail: str
    location: str = ""


@dataclass
class DiagnosticReport:
    diagnostics: list[Diagnostic] = field(default_factory=list)
    loss_notes: list[LossNote] = field(default_factory=list)

    def error(self, code: str, location: str = "", **params: object) -> None:
        self.diagnostics.append(Diagnostic.make(code, Severity.ERROR, location, **params))

    def warning(self, code: str, location: str = "", **params: object) -> None:
        self.diagnostics.append(Diagnostic.make(code, Severity.WARNING, location, **params))

    def info(self, code: str, location: str = "", **params: object) -> None:
        self.diagnostics.append(Diagnostic.make(code, Severity.INFO, location, **params))

    def loss(self, field_name: str, direction: str, kind: LossKind, detail: str,
             location: str = "") -> None:
        self.loss_notes.append(LossNote(field_name, direction, kind, detail, location))

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return any(d.severity is Severity.ERROR for d in self.diagnostics)

    def extend(self, other: "DiagnosticReport") -> None:
        self.diagnostics.extend(other.diagnostics)
        self.loss_notes.extend(other.loss_notes)

    def codes(self) -> list[str]:
        return [d.code for d in self.diagnostics]
