from __future__ import annotations

import subprocess
from pathlib import Path

from parsy.graph.models import PropertyGraph
from parsy.overview.architecture import generate_architecture_mermaid
from parsy.parse.models import ParsedFile
from parsy.walk.records import FileRecord


def save_overview(
    *,
    source: str,
    repo_root: Path,
    files: list[FileRecord],
    graph: PropertyGraph | None = None,
    parsed_files: list[ParsedFile] | None = None,
    out_dir: Path,
    endpoint: str | None = None,
    render_png: bool = False,
) -> list[Path]:
    """Save a high-level Mermaid overview independent of the symbol graph.

    The default behavior is local-only and heuristic. It emits a GitDiagram-like
    architecture overview inferred from paths, parsed symbols, imports, and
    repository artifacts.

    The endpoint parameter is intentionally a stub for a future manually supplied
    GitDiagram-compatible service. No public GitDiagram endpoint is assumed or
    called automatically.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    mermaid = generate_architecture_mermaid(
        repo_root=repo_root,
        source=source,
        files=files,
        graph=graph,
        parsed_files=parsed_files,
    )
    mmd_path = out_dir / "overview.mmd"
    mmd_path.write_text(mermaid, encoding="utf-8")
    artifacts = [mmd_path]
    if endpoint:
        stub_path = out_dir / "overview_endpoint_stub.txt"
        stub_path.write_text(endpoint_stub_message(endpoint), encoding="utf-8")
        artifacts.append(stub_path)
    if render_png:
        png_path = out_dir / "overview.png"
        if render_mermaid_png(mmd_path, png_path):
            artifacts.append(png_path)
    return artifacts


def fetch_gitdiagram_mermaid(source: str, endpoint: str) -> str:
    """Stub for a future manually supplied GitDiagram-compatible endpoint.

    Parsy intentionally does not assume that a public GitDiagram API exists.
    Implement this function manually if you deploy your own service that accepts
    {"source": "..."} and returns Mermaid text.
    """
    raise NotImplementedError(endpoint_stub_message(endpoint))


def endpoint_stub_message(endpoint: str) -> str:
    return (
        "GitDiagram-compatible endpoint integration is currently a stub.\n"
        "No HTTP request was made.\n\n"
        f"Configured endpoint: {endpoint}\n\n"
        "To enable this manually, implement fetch_gitdiagram_mermaid() in "
        "src/parsy/overview/gitdiagram.py so it calls your own diagram service "
        "and returns Mermaid text.\n"
    )


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
