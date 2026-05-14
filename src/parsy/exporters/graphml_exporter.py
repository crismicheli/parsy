from __future__ import annotations

from pathlib import Path

from parsy.exporters.networkx_exporter import to_networkx
from parsy.graph.models import PropertyGraph


def export_graphml(graph: PropertyGraph, output_path: Path) -> Path:
    try:
        import networkx as nx
    except ImportError as exc:
        raise RuntimeError("GraphML export requires installing parsy[networkx].") from exc
    g = to_networkx(graph)
    for _, attrs in g.nodes(data=True):
        _flatten(attrs)
    for _, _, _, attrs in g.edges(keys=True, data=True):
        _flatten(attrs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(g, output_path, edge_id_from_attribute="id")
    return output_path


def _flatten(attrs: dict) -> None:
    for key, value in list(attrs.items()):
        if value is None:
            attrs[key] = ""
        elif isinstance(value, (dict, list, tuple, set)):
            attrs[key] = str(value)
