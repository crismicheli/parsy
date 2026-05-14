from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Symbol:
    id: str
    kind: str
    name: str
    qualified_name: str
    file_path: Path | None
    line_start: int | None
    line_end: int | None
    scope: str | None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ImportAlias:
    local_name: str
    target: str
    source_module: str | None
    line: int

