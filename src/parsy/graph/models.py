from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Node:
    id: str
    kind: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Edge:
    source: str
    target: str
    kind: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PropertyGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def ensure_external(self, symbol_id: str) -> None:
        if symbol_id and symbol_id not in self.nodes:
            self.add_node(Node(id=symbol_id, kind="ExternalSymbol", label=symbol_id, properties={}))

