from __future__ import annotations

from pathlib import Path

from parsy.exporters.graphml_exporter import export_graphml
from parsy.exporters.json_exporter import export_json
from parsy.exporters.neo4j_exporter import export_neo4j
from parsy.exporters.networkx_exporter import export_networkx
from parsy.exporters.plantuml_exporter import export_plantuml
from parsy.exporters.symbol_inventory import export_symbol_inventory
from parsy.graph.models import PropertyGraph


def export_graph(graph: PropertyGraph, formats: list[str], out_dir: Path) -> list[Path]:
    artifacts: list[Path] = []
    for fmt in formats or ["json"]:
        if fmt == "json":
            artifacts.append(export_json(graph, out_dir / "graph.json"))
        elif fmt == "networkx":
            artifacts.append(export_networkx(graph, out_dir / "graph.networkx.pkl"))
        elif fmt == "graphml":
            artifacts.append(export_graphml(graph, out_dir / "graph.graphml"))
        elif fmt == "neo4j":
            artifacts.append(export_neo4j(graph, out_dir / "neo4j"))
        elif fmt == "plantuml":
            artifacts.append(export_plantuml(graph, out_dir / "graph.puml"))
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

    artifacts.append(export_symbol_inventory(graph, out_dir / "symbol_inventory.json"))
    return artifacts
