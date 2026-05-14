from __future__ import annotations

import re
from pathlib import Path

from parsy.graph.models import Edge, Node, PropertyGraph


def export_plantuml(graph: PropertyGraph, output_path: Path) -> Path:
    """Export a PlantUML class diagram.

    This exporter is a visualization projection, not the canonical graph store.
    It keeps symbol identity via PlantUML aliases and emphasizes class/function
    structure, inheritance, imports, aliases, and calls.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "@startuml",
        "hide empty members",
        "skinparam packageStyle rectangle",
        "skinparam classAttributeIconSize 0",
        "",
    ]

    module_nodes = [node for node in graph.nodes.values() if node.kind == "Module"]
    contained = _containment_index(graph)

    emitted: set[str] = set()
    for module in sorted(module_nodes, key=lambda node: node.id):
        lines.extend(_emit_module_package(module, graph, contained, emitted))

    for node in sorted(graph.nodes.values(), key=lambda item: item.id):
        if node.id not in emitted and node.kind in {"Class", "Function", "Method", "ExternalSymbol", "AliasSymbol"}:
            lines.extend(_emit_standalone_node(node, emitted))

    lines.append("")
    parent = _parent_index(graph)
    for edge in graph.edges:
        relation = _edge_relation(edge)
        if not relation:
            continue
        if edge.source not in graph.nodes or edge.target not in graph.nodes:
            continue
        source_id = _relation_endpoint(edge.source, graph, parent)
        target_id = _relation_endpoint(edge.target, graph, parent)
        if source_id == target_id:
            continue
        source = _alias(source_id)
        target = _alias(target_id)
        label = edge.kind
        if edge.kind == "INHERITS":
            lines.append(f"{target} <|-- {source}")
        else:
            lines.append(f"{source} {relation} {target} : {label}")

    lines.extend(["", "@enduml", ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _emit_module_package(
    module: Node,
    graph: PropertyGraph,
    contained: dict[str, list[str]],
    emitted: set[str],
) -> list[str]:
    lines = [f'package "{_escape_label(module.id)}" as {_alias(module.id)} {{']
    emitted.add(module.id)
    for child_id in sorted(contained.get(module.id, [])):
        child = graph.nodes.get(child_id)
        if child is None:
            continue
        if child.kind == "Class":
            lines.extend(_emit_class(child, graph, contained, emitted, indent="  "))
        elif child.kind == "Function":
            lines.extend(_emit_function(child, emitted, indent="  "))
        elif child.kind == "AliasSymbol":
            lines.extend(_emit_alias(child, emitted, indent="  "))
    lines.append("}")
    lines.append("")
    return lines


def _emit_class(
    node: Node,
    graph: PropertyGraph,
    contained: dict[str, list[str]],
    emitted: set[str],
    *,
    indent: str,
) -> list[str]:
    alias = _alias(node.id)
    label = _escape_label(node.label)
    lines = [f'{indent}class "{label}" as {alias} {{']
    emitted.add(node.id)
    methods = [
        graph.nodes[child_id]
        for child_id in sorted(contained.get(node.id, []))
        if child_id in graph.nodes and graph.nodes[child_id].kind == "Method"
    ]
    for method in methods:
        emitted.add(method.id)
        lines.append(f"{indent}  +{_escape_member(method.label)}()")
    lines.append(f"{indent}}}")
    return lines


def _emit_function(node: Node, emitted: set[str], *, indent: str) -> list[str]:
    emitted.add(node.id)
    return [f'{indent}class "{_escape_label(node.label)}()" as {_alias(node.id)} <<function>>']


def _emit_alias(node: Node, emitted: set[str], *, indent: str) -> list[str]:
    emitted.add(node.id)
    return [f'{indent}class "{_escape_label(node.label)}" as {_alias(node.id)} <<alias>>']


def _emit_standalone_node(node: Node, emitted: set[str]) -> list[str]:
    if node.kind == "Class":
        return _emit_class(node, PropertyGraph(nodes={node.id: node}, edges=[]), {}, emitted, indent="")
    if node.kind in {"Function", "Method"}:
        return _emit_function(node, emitted, indent="")
    if node.kind == "AliasSymbol":
        return _emit_alias(node, emitted, indent="")
    emitted.add(node.id)
    return [f'class "{_escape_label(node.label)}" as {_alias(node.id)} <<external>>']


def _containment_index(graph: PropertyGraph) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.kind == "CONTAINS":
            index.setdefault(edge.source, []).append(edge.target)
    return index


def _parent_index(graph: PropertyGraph) -> dict[str, str]:
    index: dict[str, str] = {}
    for edge in graph.edges:
        if edge.kind == "CONTAINS":
            index[edge.target] = edge.source
    return index


def _relation_endpoint(symbol_id: str, graph: PropertyGraph, parent: dict[str, str]) -> str:
    node = graph.nodes[symbol_id]
    if node.kind == "Method":
        return parent.get(symbol_id, symbol_id)
    return symbol_id


def _edge_relation(edge: Edge) -> str | None:
    return {
        "IMPORTS": "..>",
        "ALIASES": "..>",
        "CALLS": "..>",
        "DECORATES": "..>",
        "ANNOTATES_WITH": "..>",
        "INHERITS": "<|--",
    }.get(edge.kind)


def _alias(symbol_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", symbol_id)
    if not safe or safe[0].isdigit():
        safe = f"n_{safe}"
    return f"p_{safe}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_member(value: str) -> str:
    return value.replace("{", "\\{").replace("}", "\\}")
