from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ImportFact:
    module: str | None
    name: str | None
    alias: str | None
    level: int
    line: int


@dataclass(frozen=True, slots=True)
class ClassFact:
    name: str
    qualified_name: str
    bases: list[str]
    decorators: list[str]
    line_start: int
    line_end: int | None
    scope: str


@dataclass(frozen=True, slots=True)
class FunctionFact:
    name: str
    qualified_name: str
    decorators: list[str]
    annotations: list[str]
    calls: list[str]
    line_start: int
    line_end: int | None
    scope: str
    is_method: bool = False


@dataclass(slots=True)
class ParsedFile:
    path: Path
    relative_path: Path
    module_name: str
    imports: list[ImportFact] = field(default_factory=list)
    classes: list[ClassFact] = field(default_factory=list)
    functions: list[FunctionFact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

