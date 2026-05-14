from __future__ import annotations

import subprocess
from pathlib import Path

from parsy.utils.paths import ensure_dir, slugify


def is_git_url(source: str) -> bool:
    return (
        source.startswith("http://")
        or source.startswith("https://")
        or source.startswith("git@")
        or source.endswith(".git")
    )


def prepare_repository(source: str, work_dir: Path) -> Path:
    """Return a local repository path, cloning URL sources into work_dir."""
    source_path = Path(source).expanduser()
    if source_path.exists():
        return source_path.resolve()
    if not is_git_url(source):
        raise FileNotFoundError(f"Source is neither a local path nor a Git URL: {source}")
    ensure_dir(work_dir)
    target = work_dir / slugify(source)
    if target.exists():
        return target.resolve()
    clone_public_repository(source, target)
    return target.resolve()


def clone_public_repository(source: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", source, str(target)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"Failed to clone repository {source}: {message}") from exc

