from __future__ import annotations

from pathlib import Path

from parsy.config.models import SchemaConfig
from parsy.graph.models import Edge, Node, PropertyGraph
from parsy.parse.models import ParsedFile
from parsy.symbols.table import SymbolTable


def build_graph(
    repo_root: Path,
    parsed_files: list[ParsedFile],
    symbols: SymbolTable,
    schema: SchemaConfig,
) -> PropertyGraph:
    graph = PropertyGraph()
    repo_id = f"repo:{repo_root.name}"
    graph.add_node(Node(id=repo_id, kind="Repository", label=repo_root.name, properties={"path": str(repo_root)}))
    for symbol in symbols.symbols.values():
        props = dict(symbol.properties)
        if symbol.file_path:
            props["file_path"] = str(symbol.file_path)
        props["qualified_name"] = symbol.qualified_name
        props["line_start"] = symbol.line_start
        props["line_end"] = symbol.line_end
        props["scope"] = symbol.scope
        graph.add_node(Node(id=symbol.id, kind=symbol.kind, label=symbol.name, properties=props))
        if symbol.kind == "Module":
            graph.add_edge(Edge(repo_id, symbol.id, "CONTAINS", {"confidence": 1.0}))
        elif symbol.scope:
            graph.add_edge(Edge(symbol.scope, symbol.id, "CONTAINS", {"confidence": 1.0}))

    for parsed in parsed_files:
        _add_import_edges(graph, parsed, symbols, schema)
        _add_class_edges(graph, parsed, symbols, schema)
        _add_function_edges(graph, parsed, symbols, schema)
    return graph


def _add_import_edges(
    graph: PropertyGraph, parsed: ParsedFile, symbols: SymbolTable, schema: SchemaConfig
) -> None:
    for alias in symbols.imports_by_module.get(parsed.module_name, []):
        target, status = symbols.resolve_name(parsed.module_name, parsed.module_name, alias.target)
        if target is None:
            target = alias.target
        if schema.include_external_symbols:
            graph.ensure_external(target)
        if target in graph.nodes:
            graph.add_edge(
                Edge(
                    parsed.module_name,
                    target,
                    "IMPORTS",
                    {
                        "line": alias.line,
                        "local_name": alias.local_name,
                        "resolution_status": status,
                        "confidence": 1.0 if status == "resolved" else 0.5,
                    },
                )
            )
            if alias.local_name != alias.target.split(".")[-1]:
                alias_id = f"{parsed.module_name}:alias:{alias.local_name}"
                graph.add_node(
                    Node(
                        id=alias_id,
                        kind="AliasSymbol",
                        label=alias.local_name,
                        properties={
                            "module": parsed.module_name,
                            "line": alias.line,
                            "target": target,
                        },
                    )
                )
                graph.add_edge(
                    Edge(
                        parsed.module_name,
                        alias_id,
                        "CONTAINS",
                        {"line": alias.line, "confidence": 1.0},
                    )
                )
                graph.add_edge(
                    Edge(
                        alias_id,
                        target,
                        "ALIASES",
                        {"module": parsed.module_name, "line": alias.line, "resolution_status": status},
                    )
                )


def _add_class_edges(
    graph: PropertyGraph, parsed: ParsedFile, symbols: SymbolTable, schema: SchemaConfig
) -> None:
    for cls in parsed.classes:
        for base in cls.bases:
            target, status = symbols.resolve_name(parsed.module_name, cls.scope, base)
            if target is None:
                target = base
            if schema.include_external_symbols:
                graph.ensure_external(target)
            if target in graph.nodes:
                graph.add_edge(
                    Edge(
                        cls.qualified_name,
                        target,
                        "INHERITS",
                        {
                            "line": cls.line_start,
                            "raw": base,
                            "resolution_status": status,
                            "confidence": 1.0 if status == "resolved" else 0.5,
                        },
                    )
                )
        if schema.include_decorators:
            for dec in cls.decorators:
                _add_reference_edge(graph, symbols, parsed.module_name, cls.qualified_name, cls.scope, dec, "DECORATES", cls.line_start)


def _add_function_edges(
    graph: PropertyGraph, parsed: ParsedFile, symbols: SymbolTable, schema: SchemaConfig
) -> None:
    for fn in parsed.functions:
        if schema.include_calls:
            for call in fn.calls:
                _add_reference_edge(
                    graph, symbols, parsed.module_name, fn.qualified_name, fn.scope, call, "CALLS", fn.line_start
                )
        if schema.include_decorators:
            for dec in fn.decorators:
                _add_reference_edge(
                    graph, symbols, parsed.module_name, fn.qualified_name, fn.scope, dec, "DECORATES", fn.line_start
                )
        if schema.include_annotations:
            for ann in fn.annotations:
                _add_reference_edge(
                    graph,
                    symbols,
                    parsed.module_name,
                    fn.qualified_name,
                    fn.scope,
                    ann,
                    "ANNOTATES_WITH",
                    fn.line_start,
                )


def _add_reference_edge(
    graph: PropertyGraph,
    symbols: SymbolTable,
    module_name: str,
    source: str,
    scope: str,
    raw_target: str,
    kind: str,
    line: int,
) -> None:
    target, status = symbols.resolve_name(module_name, scope, raw_target)
    if target is None:
        target = raw_target
    graph.ensure_external(target)
    graph.add_edge(
        Edge(
            source,
            target,
            kind,
            {
                "line": line,
                "raw": raw_target,
                "resolution_status": status,
                "confidence": 1.0 if status == "resolved" else 0.4,
            },
        )
    )
