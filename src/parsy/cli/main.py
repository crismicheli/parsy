from __future__ import annotations

from pathlib import Path

import click

from parsy.config import ParsyConfig
from parsy.pipeline.run import BatchAnalysisResult, analyze, analyze_many, read_sources_file


@click.group()
def main() -> None:
    """Generate symbol graphs from source repositories."""


@main.command()
@click.argument("source", type=str)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("outputs/parsy"))
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--language", type=click.Choice(["python", "typescript", "javascript"]), default=None)
@click.option(
    "--format",
    "formats",
    multiple=True,
    type=click.Choice(["json", "networkx", "graphml", "neo4j", "plantuml"]),
    help="Export format. Can be provided multiple times. Defaults to JSON.",
)
@click.option(
    "--granularity",
    type=click.Choice(["low", "medium", "high"]),
    default=None,
    help="Graph detail level. Defaults to medium.",
)
@click.option("--verbose", "-v", is_flag=True, help="Print high-level pipeline progress.")
@click.option("--overview/--no-overview", default=None, help="Generate high-level Mermaid overview.")
@click.option("--overview-endpoint", default=None, help="Reserved stub for a future manual GitDiagram-compatible endpoint.")
@click.option("--overview-png/--no-overview-png", default=None, help="Render Mermaid overview to PNG.")
def analyze_cmd(
    source: str,
    out_dir: Path,
    config_path: Path | None,
    language: str | None,
    formats: tuple[str, ...],
    granularity: str | None,
    verbose: bool,
    overview: bool | None,
    overview_endpoint: str | None,
    overview_png: bool | None,
) -> None:
    """Analyze SOURCE, a local path or public Git URL."""
    cfg = _config_from_options(
        config_path=config_path,
        language=language,
        formats=formats,
        overview=overview,
        overview_endpoint=overview_endpoint,
        overview_png=overview_png,
        granularity=granularity,
        verbose=verbose,
    )
    result = analyze(source, out_dir=out_dir, config=cfg)
    click.echo(f"Repository: {result.repo_path}")
    click.echo(f"Files analyzed: {result.files_analyzed}")
    click.echo(f"Nodes: {result.node_count}")
    click.echo(f"Edges: {result.edge_count}")
    click.echo("Artifacts:")
    for artifact in result.artifacts:
        click.echo(f"  - {artifact}")


@main.command("analyze-many")
@click.argument("sources", nargs=-1, type=str, required=True)
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("outputs/parsy-batch"))
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--language", type=click.Choice(["python", "typescript", "javascript"]), default=None)
@click.option(
    "--format",
    "formats",
    multiple=True,
    type=click.Choice(["json", "networkx", "graphml", "neo4j", "plantuml"]),
    help="Export format. Can be provided multiple times. Defaults to JSON.",
)
@click.option(
    "--granularity",
    type=click.Choice(["low", "medium", "high"]),
    default=None,
    help="Graph detail level. Defaults to medium.",
)
@click.option("--verbose", "-v", is_flag=True, help="Print high-level pipeline progress.")
@click.option("--overview/--no-overview", default=None, help="Generate high-level Mermaid overview.")
@click.option("--overview-endpoint", default=None, help="Reserved stub for a future manual GitDiagram-compatible endpoint.")
@click.option("--overview-png/--no-overview-png", default=None, help="Render Mermaid overview to PNG.")
def analyze_many_cmd(
    sources: tuple[str, ...],
    out_dir: Path,
    config_path: Path | None,
    language: str | None,
    formats: tuple[str, ...],
    granularity: str | None,
    verbose: bool,
    overview: bool | None,
    overview_endpoint: str | None,
    overview_png: bool | None,
) -> None:
    """Analyze multiple SOURCES, each a local path or public Git URL."""
    cfg = _config_from_options(
        config_path=config_path,
        language=language,
        formats=formats,
        overview=overview,
        overview_endpoint=overview_endpoint,
        overview_png=overview_png,
        granularity=granularity,
        verbose=verbose,
    )
    _print_batch_result(analyze_many(sources, out_dir=out_dir, config=cfg))


@main.command("analyze-list")
@click.argument("sources_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=Path("outputs/parsy-batch"))
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--language", type=click.Choice(["python", "typescript", "javascript"]), default=None)
@click.option(
    "--format",
    "formats",
    multiple=True,
    type=click.Choice(["json", "networkx", "graphml", "neo4j", "plantuml"]),
    help="Export format. Can be provided multiple times. Defaults to JSON.",
)
@click.option(
    "--granularity",
    type=click.Choice(["low", "medium", "high"]),
    default=None,
    help="Graph detail level. Defaults to medium.",
)
@click.option("--verbose", "-v", is_flag=True, help="Print high-level pipeline progress.")
@click.option("--overview/--no-overview", default=None, help="Generate high-level Mermaid overview.")
@click.option("--overview-endpoint", default=None, help="Reserved stub for a future manual GitDiagram-compatible endpoint.")
@click.option("--overview-png/--no-overview-png", default=None, help="Render Mermaid overview to PNG.")
def analyze_list_cmd(
    sources_file: Path,
    out_dir: Path,
    config_path: Path | None,
    language: str | None,
    formats: tuple[str, ...],
    granularity: str | None,
    verbose: bool,
    overview: bool | None,
    overview_endpoint: str | None,
    overview_png: bool | None,
) -> None:
    """Analyze newline-delimited sources from SOURCES_FILE."""
    sources = read_sources_file(sources_file)
    cfg = _config_from_options(
        config_path=config_path,
        language=language,
        formats=formats,
        overview=overview,
        overview_endpoint=overview_endpoint,
        overview_png=overview_png,
        granularity=granularity,
        verbose=verbose,
    )
    _print_batch_result(analyze_many(sources, out_dir=out_dir, config=cfg))


def _config_from_options(
    *,
    config_path: Path | None,
    language: str | None,
    formats: tuple[str, ...],
    overview: bool | None,
    overview_endpoint: str | None,
    overview_png: bool | None,
    granularity: str | None,
    verbose: bool | None,
) -> ParsyConfig:
    return ParsyConfig.from_file(config_path).with_cli_overrides(
        language=language,
        formats=formats or None,
        overview=overview,
        overview_endpoint=overview_endpoint,
        overview_png=overview_png,
        granularity=granularity,
        verbose=verbose,
    )


def _print_batch_result(batch: BatchAnalysisResult) -> None:
    click.echo(f"Repositories analyzed: {len(batch.items)}")
    click.echo(f"Total files analyzed: {batch.total_files_analyzed}")
    click.echo(f"Total nodes: {batch.total_node_count}")
    click.echo(f"Total edges: {batch.total_edge_count}")
    for item in batch.items:
        click.echo("")
        click.echo(f"Source: {item.source}")
        click.echo(f"Output: {item.out_dir}")
        click.echo(f"Repository: {item.result.repo_path}")
        click.echo(f"Files analyzed: {item.result.files_analyzed}")
        click.echo(f"Nodes: {item.result.node_count}")
        click.echo(f"Edges: {item.result.edge_count}")
        click.echo("Artifacts:")
        for artifact in item.result.artifacts:
            click.echo(f"  - {artifact}")


if __name__ == "__main__":
    main()
