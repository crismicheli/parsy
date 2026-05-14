from __future__ import annotations

from parsy.graph.models import Edge, Node, PropertyGraph


VIEW_RULES: dict[str, dict[str, set[str] | bool]] = {
    "dependency": {
        "nodes": {"Module", "Class", "Function", "Method", "ExternalSymbol"},
        "edges": {"IMPORTS", "INHERITS", "CALLS"},
        "connected_only": True,
    },
    "module": {
        "nodes": {"Module", "ExternalSymbol"},
        "edges": {"IMPORTS"},
        "connected_only": True,
    },
    "class": {
        "nodes": {"Module", "Class", "ExternalSymbol"},
        "edges": {"CONTAINS", "IMPORTS", "INHERITS"},
        "connected_only": False,
    },
    "function": {
        "nodes": {"Function", "Method", "ExternalSymbol"},
        "edges": {"CALLS"},
        "connected_only": True,
    },
}


def project_graph(graph: PropertyGraph, view: str) -> PropertyGraph:
    """Project the canonical internal graph into an exported external view.

    Granularity controls what is extracted into the canonical graph. Projection
    controls what schema is exported for visualization or downstream use.
    """
    if view == "full":
        return _copy_graph(graph)
    if view not in VIEW_RULES:
        raise ValueError(f"Unknown graph view: {view}")

    rules = VIEW_RULES[view]
    allowed_nodes = rules["nodes"]
    allowed_edges = rules["edges"]
    connected_only = bool(rules["connected_only"])

    if not isinstance(allowed_nodes, set) or not isinstance(allowed_edges, set):
        raise TypeError("Projection rules are malformed.")

    projected = PropertyGraph()
    for node in graph.nodes.values():
        if node.kind in allowed_nodes:
            projected.add_node(_copy_node(node))

    projected.edges = [
        _copy_edge(edge)
        for edge in graph.edges
        if edge.kind in allowed_edges
        and edge.source in projected.nodes
        and edge.target in projected.nodes
        and _edge_allowed_for_view(edge, view, projected)
    ]

    if connected_only:
        _drop_isolated_nodes(projected)
    return projected


def _edge_allowed_for_view(edge: Edge, view: str, graph: PropertyGraph) -> bool:
    if view == "class" and edge.kind == "CONTAINS":
        source = graph.nodes.get(edge.source)
        target = graph.nodes.get(edge.target)
        return bool(source and target and source.kind == "Module" and target.kind == "Class")
    return True


def _drop_isolated_nodes(graph: PropertyGraph) -> None:
    connected: set[str] = set()
    for edge in graph.edges:
        connected.add(edge.source)
        connected.add(edge.target)
    graph.nodes = {node_id: node for node_id, node in graph.nodes.items() if node_id in connected}


def _copy_graph(graph: PropertyGraph) -> PropertyGraph:
    copied = PropertyGraph()
    for node in graph.nodes.values():
        copied.add_node(_copy_node(node))
    for edge in graph.edges:
        copied.add_edge(_copy_edge(edge))
    return copied


def _copy_node(node: Node) -> Node:
    return Node(
        id=node.id,
        kind=node.kind,
        label=node.label,
        properties=dict(node.properties),
    )


def _copy_edge(edge: Edge) -> Edge:
    return Edge(
        source=edge.source,
        target=edge.target,
        kind=edge.kind,
        properties=dict(edge.properties),
    )
