from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileRecord:
    path: Path
    relative_path: Path
    language: str
    size_bytes: int

