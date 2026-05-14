from __future__ import annotations

import re
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(value: str) -> str:
    value = value.strip().rstrip("/")
    value = value.replace("https://", "").replace("http://", "")
    value = value.replace("git@", "").replace(":", "/")
    value = re.sub(r"\.git$", "", value)
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
    return value.strip("-") or "repo"


def module_name_from_path(repo_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(repo_root)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)

