from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from parsy.config import ParsyConfig
from parsy.exporters import export_graph
from parsy.graph import build_graph, project_graph
from parsy.ingest import prepare_repository
from parsy.overview import save_overview
from parsy.parse import parser_for_language
from parsy.symbols import build_symbol_table
from parsy.utils.paths import ensure_dir, slugify
from parsy.walk import walk_repository


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    repo_path: Path
    files_analyzed: int
    node_count: int
    edge_count: int
    artifacts: list[Path]


@dataclass(frozen=True, slots=True)
class BatchAnalysisItem:
    source: str
    out_dir: Path
    result: AnalysisResult


@dataclass(frozen=True, slots=True)
class BatchAnalysisResult:
    items: list[BatchAnalysisItem]

    @property
    def total_files_analyzed(self) -> int:
        return sum(item.result.files_analyzed for item in self.items)

    @property
    def total_node_count(self) -> int:
        return sum(item.result.node_count for item in self.items)

    @property
    def total_edge_count(self) -> int:
        return sum(item.result.edge_count for item in self.items)


def analyze(source: str, *, out_dir: Path, config: ParsyConfig | None = None) -> AnalysisResult:
    cfg = config or ParsyConfig()
    cfg.schema.apply_granularity()
    out_dir = ensure_dir(out_dir)

    _log(cfg, "Parsing in progress. Parsy is preparing the repository analysis pipeline.")
    _log(cfg, f"Preparing repository: {source}")
    repo_path = prepare_repository(source, cfg.work_dir)

    _log(cfg, f"Walking {cfg.language} files under: {repo_path}")
    files = walk_repository(repo_path, cfg.walk, cfg.language)
    _log(cfg, f"Selected {len(files)} files for analysis")

    _log(cfg, "Initializing parser")
    parser = parser_for_language(cfg.language)

    _log(cfg, "Parsing source files")
    parsed_files = [parser.parse_file(repo_path, record) for record in files]

    _log(cfg, "Building symbol table")
    symbols = build_symbol_table(parsed_files)

    _log(cfg, f"Building internal graph with granularity={cfg.schema.granularity}")
    graph = build_graph(repo_path, parsed_files, symbols, cfg.schema)
    _log(cfg, f"Internal graph built: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    _log(cfg, f"Projecting exported graph with view={cfg.schema.view}")
    export_graph_view = project_graph(graph, cfg.schema.view)
    _log(
        cfg,
        f"Projected graph ready: {len(export_graph_view.nodes)} nodes, "
        f"{len(export_graph_view.edges)} edges",
    )

    _log(cfg, f"Exporting graph formats: {', '.join(cfg.exports.formats or ['json'])}")
    artifacts = export_graph(export_graph_view, cfg.exports.formats, out_dir)

    if cfg.overview.enabled:
        _log(cfg, "Generating optional high-level Mermaid overview")
        artifacts.extend(
            save_overview(
                source=source,
                repo_root=repo_path,
                files=files,
                graph=graph,
                parsed_files=parsed_files,
                out_dir=out_dir / "overview",
                endpoint=cfg.overview.endpoint,
                render_png=cfg.overview.render_png,
            )
        )

    _log(cfg, "Analysis complete")
    return AnalysisResult(
        repo_path=repo_path,
        files_analyzed=len(files),
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        artifacts=artifacts,
    )


def analyze_many(
    sources: list[str] | tuple[str, ...],
    *,
    out_dir: Path,
    config: ParsyConfig | None = None,
) -> BatchAnalysisResult:
    """Analyze multiple repositories, writing one graph bundle per source."""
    if not sources:
        raise ValueError("At least one source is required.")
    out_dir = ensure_dir(out_dir)
    used: set[str] = set()
    items: list[BatchAnalysisItem] = []
    for source in sources:
        source_out = out_dir / _unique_slug(source, used)
        result = analyze(source, out_dir=source_out, config=config)
        items.append(BatchAnalysisItem(source=source, out_dir=source_out, result=result))
    return BatchAnalysisResult(items=items)


def read_sources_file(path: Path) -> list[str]:
    """Read newline-delimited repo sources, ignoring blank lines and comments."""
    sources: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        sources.append(line)
    return sources


def _unique_slug(source: str, used: set[str]) -> str:
    base = slugify(source)
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}-{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def _log(config: ParsyConfig, message: str) -> None:
    print(f"[parsy] {message}")
