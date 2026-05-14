from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from parsy.config.models import WalkConfig
from parsy.walk.records import FileRecord


def detect_language(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in {".ts", ".tsx"}:
        return "typescript"
    if suffix in {".js", ".jsx"}:
        return "javascript"
    return None


def walk_repository(repo_root: Path, config: WalkConfig, language: str) -> list[FileRecord]:
    records: list[FileRecord] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root)
        rel_posix = rel.as_posix()
        if not _included(rel_posix, config.include):
            continue
        if _excluded(rel_posix, config.exclude):
            continue
        detected = detect_language(path)
        if detected != language:
            continue
        records.append(
            FileRecord(
                path=path,
                relative_path=rel,
                language=detected,
                size_bytes=path.stat().st_size,
            )
        )
    return records


def _included(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def _excluded(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)

