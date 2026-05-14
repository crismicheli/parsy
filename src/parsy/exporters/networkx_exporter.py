from __future__ import annotations

import pickle
from pathlib import Path

from parsy.graph.models import PropertyGraph


def to_networkx(graph: PropertyGraph):
    try:
        import networkx as nx
    except ImportError as exc:
        raise RuntimeError("NetworkX export requires installing parsy[networkx].") from exc
    g = nx.MultiDiGraph()
    for node in graph.nodes.values():
        g.add_node(node.id, kind=node.kind, label=node.label, **node.properties)
    for edge in graph.edges:
        g.add_edge(edge.source, edge.target, kind=edge.kind, **edge.properties)
    return g


def export_networkx(graph: PropertyGraph, output_path: Path) -> Path:
    g = to_networkx(graph)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as fh:
        pickle.dump(g, fh)
    return output_path

