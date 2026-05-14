from __future__ import annotations

import subprocess
from pathlib import Path

import requests

from parsy.walk.records import FileRecord


def save_overview(
    *,
    source: str,
    files: list[FileRecord],
    out_dir: Path,
    endpoint: str | None = None,
    render_png: bool = False,
) -> list[Path]:
    """Save a high-level Mermaid overview independent of the symbol graph.

    If endpoint is provided, parsy calls it as a GitDiagram-compatible API using
    JSON payload {"source": source}. The response can be raw Mermaid text or JSON
    with a "mermaid" field. Without endpoint, parsy emits a small deterministic
    file-tree overview as Mermaid.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    mermaid = fetch_gitdiagram_mermaid(source, endpoint) if endpoint else fallback_mermaid(files)
    mmd_path = out_dir / "overview.mmd"
    mmd_path.write_text(mermaid, encoding="utf-8")
    artifacts = [mmd_path]
    if render_png:
        png_path = out_dir / "overview.png"
        if render_mermaid_png(mmd_path, png_path):
            artifacts.append(png_path)
    return artifacts


def fetch_gitdiagram_mermaid(source: str, endpoint: str) -> str:
    response = requests.post(endpoint, json={"source": source}, timeout=120)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        if "mermaid" not in data:
            raise ValueError("GitDiagram-compatible endpoint JSON must contain a 'mermaid' field.")
        return data["mermaid"]
    return response.text


def fallback_mermaid(files: list[FileRecord]) -> str:
    by_top_level: dict[str, int] = {}
    for record in files:
        top = record.relative_path.parts[0] if record.relative_path.parts else "."
        by_top_level[top] = by_top_level.get(top, 0) + 1
    lines = ["flowchart TD", "  repo[Repository]"]
    for index, (name, count) in enumerate(sorted(by_top_level.items())):
        node = f"n{index}"
        label = f"{name}<br/>{count} files"
        lines.append(f"  {node}[\"{label}\"]")
        lines.append(f"  repo --> {node}")
    return "\n".join(lines) + "\n"


def render_mermaid_png(mmd_path: Path, png_path: Path) -> bool:
    """Render Mermaid to PNG using mmdc if installed."""
    try:
        subprocess.run(
            ["mmdc", "-i", str(mmd_path), "-o", str(png_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True

