from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from parsy.graph.models import PropertyGraph
from parsy.parse.models import ParsedFile
from parsy.walk.file_walker import EXCLUDED_PARTS
from parsy.walk.records import FileRecord


@dataclass(frozen=True, slots=True)
class OverviewNode:
    id: str
    group: str
    title: str
    subtitle: str
    relative_path: str | None
    key_symbols: tuple[str, ...] = ()
    shape: str = "rect"


@dataclass(frozen=True, slots=True)
class OverviewEdge:
    source: str
    target: str
    label: str
    dotted: bool = False


GROUP_TITLES = {
    "config": "Config",
    "core": "Core engine",
    "classifiers": "Classifiers",
    "plotting": "Plotting",
    "workflows": "Scripts",
    "artifacts": "Artifacts",
    "tests": "Tests",
    "other": "Other",
}

GROUP_CLASSES = {
    "config": "toneBlue",
    "core": "toneAmber",
    "classifiers": "toneMint",
    "plotting": "toneRose",
    "workflows": "toneIndigo",
    "artifacts": "toneTeal",
    "tests": "toneNeutral",
    "other": "toneNeutral",
}


def generate_architecture_mermaid(
    *,
    repo_root: Path,
    source: str,
    files: list[FileRecord],
    graph: PropertyGraph | None = None,
    parsed_files: list[ParsedFile] | None = None,
) -> str:
    key_symbols = _key_symbols_by_path(graph)
    nodes = _build_nodes(repo_root, files, key_symbols)
    edges = _build_edges(nodes, graph, parsed_files or [])
    return _render_mermaid(nodes, edges, source)


def _build_nodes(
    repo_root: Path,
    files: list[FileRecord],
    key_symbols: dict[str, tuple[str, ...]],
) -> list[OverviewNode]:
    nodes: list[OverviewNode] = []
    seen_paths: set[str] = set()
    for record in files:
        if _skip_path(record.relative_path):
            continue
        rel = record.relative_path.as_posix()
        seen_paths.add(rel)
        group = _classify_group(record.relative_path)
        title = _human_title(record.relative_path)
        subtitle = _subtitle(record.relative_path)
        nodes.append(
            OverviewNode(
                id=_node_id(rel),
                group=group,
                title=title,
                subtitle=subtitle,
                relative_path=rel,
                key_symbols=_symbols_for_rel(rel, key_symbols),
            )
        )

    for artifact_path, title, subtitle, shape in _artifact_candidates(repo_root):
        rel = artifact_path.as_posix()
        if rel in seen_paths:
            continue
        nodes.append(
            OverviewNode(
                id=_node_id(rel),
                group="artifacts",
                title=title,
                subtitle=subtitle,
                relative_path=rel,
                shape=shape,
            )
        )
    return sorted(nodes, key=lambda node: (node.group, node.relative_path or node.id))


def _build_edges(
    nodes: list[OverviewNode],
    graph: PropertyGraph | None,
    parsed_files: list[ParsedFile],
) -> list[OverviewEdge]:
    by_path = {node.relative_path: node for node in nodes if node.relative_path}
    by_module = _module_node_index(nodes)
    edges: dict[tuple[str, str, str, bool], OverviewEdge] = {}

    if graph is not None:
        for edge in graph.edges:
            if edge.kind not in {"IMPORTS", "CALLS", "INHERITS"}:
                continue
            source_node = _node_for_graph_symbol(edge.source, graph, by_path, by_module)
            target_node = _node_for_graph_symbol(edge.target, graph, by_path, by_module)
            if source_node is None or target_node is None or source_node.id == target_node.id:
                continue
            label = _edge_label(source_node, target_node, edge.kind)
            item = OverviewEdge(source_node.id, target_node.id, label)
            edges[(item.source, item.target, item.label, item.dotted)] = item

    _add_parsed_call_edges(edges, by_module, parsed_files)

    nodes_by_group: dict[str, list[OverviewNode]] = {}
    for node in nodes:
        nodes_by_group.setdefault(node.group, []).append(node)

    _add_role_edges(nodes_by_group, edges)
    return sorted(edges.values(), key=lambda edge: (edge.source, edge.target, edge.label))


def _add_role_edges(
    nodes_by_group: dict[str, list[OverviewNode]],
    edges: dict[tuple[str, str, str, bool], OverviewEdge],
) -> None:
    core_nodes = nodes_by_group.get("core", [])
    config_nodes = nodes_by_group.get("config", [])
    plotting_nodes = nodes_by_group.get("plotting", [])
    classifier_nodes = nodes_by_group.get("classifiers", [])
    workflow_nodes = nodes_by_group.get("workflows", [])
    artifact_nodes = nodes_by_group.get("artifacts", [])

    simulation = _find_first(core_nodes, ["simulation", "simulate", "engine", "model"])
    viability = _find_first(core_nodes, ["viability", "analysis"])
    classifier = _find_first(classifier_nodes, ["dispatch", "classifier"])
    plot_helper = _find_first(plotting_nodes, ["helper", "plot"])
    figures = _find_first(artifact_nodes, ["figure", "output"])
    docs = _find_first(artifact_nodes, ["doc", "readme"])
    notebook = _find_first(artifact_nodes, ["notebook", "explore"])

    for node in config_nodes:
        if simulation:
            _store_edge(edges, node.id, simulation.id, "parameters")
    if simulation and viability:
        _store_edge(edges, simulation.id, viability.id, "produces")
    if viability and classifier:
        _store_edge(edges, viability.id, classifier.id, "classifies")
    if plot_helper:
        for workflow in workflow_nodes:
            _store_edge(edges, plot_helper.id, workflow.id, "used by")
    for workflow in workflow_nodes:
        if figures:
            _store_edge(edges, workflow.id, figures.id, "writes")
    if docs:
        for workflow in workflow_nodes[:6]:
            _store_edge(edges, docs.id, workflow.id, "documents", dotted=True)
    if notebook and core_nodes:
        _store_edge(edges, notebook.id, core_nodes[0].id, "explores", dotted=True)


def _render_mermaid(nodes: list[OverviewNode], edges: list[OverviewEdge], source: str) -> str:
    lines = ["flowchart TD", ""]
    for group in _ordered_groups(nodes):
        group_nodes = [node for node in nodes if node.group == group]
        if not group_nodes:
            continue
        lines.append(f'subgraph group_{group}["{GROUP_TITLES.get(group, group.title())}"]')
        for node in group_nodes:
            label_parts = [node.title, node.subtitle]
            if node.key_symbols:
                label_parts.append("Key: " + ", ".join(node.key_symbols))
            if node.relative_path and node.relative_path.endswith(".py"):
                label_parts.append(f"[{Path(node.relative_path).name}]")
            label = _escape_label("<br/>".join(label_parts))
            if node.shape == "database":
                lines.append(f'  {node.id}[("{label}")]')
            else:
                lines.append(f'  {node.id}["{label}"]')
        lines.append("end")
        lines.append("")

    for edge in edges:
        arrow = "-.->" if edge.dotted else "-->"
        lines.append(f'{edge.source} {arrow}|"{_escape_label(edge.label)}"| {edge.target}')

    click_lines = _click_lines(nodes, source)
    if click_lines:
        lines.append("")
        lines.extend(click_lines)

    lines.append("")
    lines.extend(_class_defs(nodes))
    return "\n".join(lines) + "\n"


def _ordered_groups(nodes: list[OverviewNode]) -> list[str]:
    preferred = ["config", "core", "classifiers", "plotting", "workflows", "artifacts", "tests", "other"]
    present = {node.group for node in nodes}
    return [group for group in preferred if group in present] + sorted(present - set(preferred))


def _class_defs(nodes: list[OverviewNode]) -> list[str]:
    lines = [
        "classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a",
        "classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554",
        "classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f",
        "classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d",
        "classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337",
        "classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81",
        "classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a",
    ]
    for group in _ordered_groups(nodes):
        ids = [node.id for node in nodes if node.group == group]
        if ids:
            lines.append(f"class {','.join(ids)} {GROUP_CLASSES.get(group, 'toneNeutral')}")
    return lines


def _click_lines(nodes: list[OverviewNode], source: str) -> list[str]:
    base = _github_blob_base(source)
    if base is None:
        return []
    lines: list[str] = []
    for node in nodes:
        if not node.relative_path:
            continue
        kind = "tree" if not node.relative_path.endswith(".py") and "." not in Path(node.relative_path).name else "blob"
        url = base.replace("/blob/", f"/{kind}/") + node.relative_path
        lines.append(f'click {node.id} "{url}"')
    return lines


def _github_blob_base(source: str) -> str | None:
    cleaned = source.rstrip("/")
    match = re.match(r"https://github\.com/([^/]+)/([^/.]+)(?:\.git)?$", cleaned)
    if not match:
        return None
    owner, repo = match.groups()
    return f"https://github.com/{owner}/{repo}/blob/main/"


def _artifact_candidates(repo_root: Path) -> list[tuple[Path, str, str, str]]:
    candidates: list[tuple[Path, str, str, str]] = []
    checks = [
        (Path("figures"), "Figures", "generated output", "database"),
        (Path("outputs"), "Outputs", "generated output", "database"),
        (Path("notebooks"), "Notebooks", "exploration", "rect"),
        (Path("docs"), "Docs", "workflow notes", "rect"),
        (Path("README.md"), "README", "project notes", "rect"),
    ]
    for rel, title, subtitle, shape in checks:
        path = repo_root / rel
        if path.exists() and not _skip_path(rel):
            candidates.append((rel, title, subtitle, shape))
    return candidates


def _module_node_index(nodes: list[OverviewNode]) -> dict[str, OverviewNode]:
    index: dict[str, OverviewNode] = {}
    for node in nodes:
        if not node.relative_path or not node.relative_path.endswith(".py"):
            continue
        path = Path(node.relative_path)
        parts = list(path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            index[".".join(parts)] = node
    return index


def _node_for_graph_symbol(
    symbol_id: str,
    graph: PropertyGraph,
    by_path: dict[str, OverviewNode],
    by_module: dict[str, OverviewNode],
) -> OverviewNode | None:
    node = graph.nodes.get(symbol_id)
    if node is not None:
        file_path = node.properties.get("file_path")
        if file_path:
            for rel, overview_node in by_path.items():
                if str(file_path).replace("\\", "/").endswith(rel):
                    return overview_node
    parts = symbol_id.split(".")
    while parts:
        module = ".".join(parts)
        if module in by_module:
            return by_module[module]
        parts.pop()
    return None


def _key_symbols_by_path(graph: PropertyGraph | None) -> dict[str, tuple[str, ...]]:
    if graph is None:
        return {}
    by_path: dict[str, list[str]] = {}
    for node in graph.nodes.values():
        if node.kind not in {"Class", "Function"}:
            continue
        file_path = node.properties.get("file_path")
        if not file_path:
            continue
        rel = str(file_path).replace("\\", "/")
        label = node.label + ("()" if node.kind == "Function" and not node.label.endswith(")") else "")
        by_path.setdefault(rel, [])
        if label not in by_path[rel]:
            by_path[rel].append(label)

    compact: dict[str, tuple[str, ...]] = {}
    for full_path, symbols in by_path.items():
        for marker in ["/config/", "/classifiers/", "/plotting/", "/scripts/", "/viabilitykernels/", "/src/"]:
            if marker in full_path:
                rel = full_path.split(marker, 1)[1]
                prefix = marker.strip("/")
                compact[f"{prefix}/{rel}"] = tuple(symbols[:3])
        compact[full_path] = tuple(symbols[:3])
    return compact


def _symbols_for_rel(relative_path: str, key_symbols: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if relative_path in key_symbols:
        return key_symbols[relative_path]
    for path, symbols in key_symbols.items():
        if path.endswith(relative_path):
            return symbols
    return ()


def _add_parsed_call_edges(
    edges: dict[tuple[str, str, str, bool], OverviewEdge],
    by_module: dict[str, OverviewNode],
    parsed_files: list[ParsedFile],
) -> None:
    if not parsed_files:
        return
    symbol_to_module: dict[str, str] = {}
    module_import_aliases: dict[str, dict[str, str]] = {}
    for parsed in parsed_files:
        for cls in parsed.classes:
            symbol_to_module[cls.name] = parsed.module_name
            symbol_to_module[cls.qualified_name] = parsed.module_name
        for fn in parsed.functions:
            symbol_to_module[fn.name] = parsed.module_name
            symbol_to_module[fn.qualified_name] = parsed.module_name
        aliases: dict[str, str] = {}
        for imp in parsed.imports:
            local_name = imp.alias or imp.name or (imp.module.split(".")[0] if imp.module else "")
            target_parts = []
            if imp.module:
                target_parts.append(imp.module)
            if imp.name and imp.name != "*":
                target_parts.append(imp.name)
            if local_name and target_parts:
                aliases[local_name] = ".".join(target_parts)
        module_import_aliases[parsed.module_name] = aliases

    for parsed in parsed_files:
        source_node = by_module.get(parsed.module_name)
        if source_node is None:
            continue
        aliases = module_import_aliases.get(parsed.module_name, {})
        local_symbols = {
            cls.name for cls in parsed.classes
        } | {
            fn.name for fn in parsed.functions
        }
        for fn in parsed.functions:
            for call in fn.calls:
                target_module = _resolve_call_module(call, parsed.module_name, local_symbols, aliases, symbol_to_module, by_module)
                if target_module is None or target_module == parsed.module_name:
                    continue
                target_node = by_module.get(target_module)
                if target_node is None:
                    continue
                _store_edge(edges, source_node.id, target_node.id, "calls")


def _resolve_call_module(
    call: str,
    current_module: str,
    local_symbols: set[str],
    aliases: dict[str, str],
    symbol_to_module: dict[str, str],
    by_module: dict[str, OverviewNode],
) -> str | None:
    first = call.split(".")[0]
    if first in local_symbols:
        return current_module
    if first in aliases:
        target = aliases[first]
        parts = target.split(".")
        while parts:
            candidate = ".".join(parts)
            if candidate in by_module:
                return candidate
            parts.pop()
    if call in symbol_to_module:
        return symbol_to_module[call]
    if first in symbol_to_module:
        return symbol_to_module[first]
    parts = call.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in by_module:
            return candidate
        parts.pop()
    return None


def _classify_group(path: Path) -> str:
    parts = [part.lower() for part in path.parts]
    name = path.stem.lower()
    joined = "/".join(parts)
    if any(part in {"config", "configs", "settings"} for part in parts):
        return "config"
    if any(part in {"classifiers", "classifier", "classification"} for part in parts):
        return "classifiers"
    if any(part in {"plotting", "plots", "visualization", "visualisation", "viz"} for part in parts):
        return "plotting"
    if any(part in {"scripts", "workflows", "examples", "bin"} for part in parts):
        return "workflows"
    if any(part in {"docs", "notebooks", "figures", "outputs"} for part in parts):
        return "artifacts"
    if any(part in {"tests", "test"} for part in parts) or name.startswith("test_"):
        return "tests"
    if any(token in joined for token in ["core", "engine", "simulation", "viability", "ode", "model"]):
        return "core"
    if len(parts) <= 2 and path.suffix == ".py":
        return "core"
    return "other"


def _human_title(path: Path) -> str:
    stem = path.stem
    if stem == "__init__":
        parent = path.parent.name or "Package"
        return f"{_title_words(parent)} API"
    replacements = {
        "odes": "ODEs",
        "api": "API",
        "cli": "CLI",
        "utils": "Utilities",
        "helpers": "Helpers",
    }
    parts = [replacements.get(part, part.title()) for part in re.split(r"[_\\-]+", stem) if part]
    return " ".join(parts) or path.name


def _subtitle(path: Path) -> str:
    stem = path.stem.lower()
    group = _classify_group(path)
    if stem == "__init__":
        return "package API"
    if "default" in stem or "param" in stem:
        return "params module"
    if "scenario" in stem:
        return "scenario presets" if group == "config" else "scenario viz"
    if "dispatch" in stem:
        return "classifier router"
    if "classifier" in stem:
        return "classifier"
    if "simulation" in stem or "simulate" in stem:
        return "trajectory engine"
    if "viability" in stem:
        return "analysis module"
    if "phase" in stem or "plane" in stem:
        return "geometry viz"
    if stem in {"ode", "odes"} or stem.endswith("_odes") or stem.startswith("odes_"):
        return "dynamics module"
    if "plot" in stem or "helper" in stem:
        return "viz primitives"
    if group == "workflows":
        return "workflow script"
    if group == "tests":
        return "test module"
    return "module"


def _edge_label(source: OverviewNode, target: OverviewNode, kind: str) -> str:
    if source.relative_path and source.relative_path.endswith("__init__.py"):
        return "re-exports" if source.group in {"config", "other"} else "exposes"
    if source.group == "config":
        return "parameters"
    if target.group == "plotting":
        return "renders"
    if source.group == "workflows":
        return "uses"
    if kind == "IMPORTS":
        return "imports"
    if kind == "CALLS":
        return "calls"
    if kind == "INHERITS":
        return "extends"
    return kind.lower()


def _find_first(nodes: list[OverviewNode], tokens: list[str]) -> OverviewNode | None:
    for token in tokens:
        for node in nodes:
            haystack = f"{node.title} {node.subtitle} {node.relative_path or ''}".lower()
            if token in haystack:
                return node
    return None


def _store_edge(
    edges: dict[tuple[str, str, str, bool], OverviewEdge],
    source: str,
    target: str,
    label: str,
    *,
    dotted: bool = False,
) -> None:
    if source == target:
        return
    edge = OverviewEdge(source, target, label, dotted)
    edges[(edge.source, edge.target, edge.label, edge.dotted)] = edge


def _node_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    if not safe or safe[0].isdigit():
        safe = f"n_{safe}"
    return f"node_{safe}"


def _title_words(value: str) -> str:
    return " ".join(part.title() for part in re.split(r"[_\\-]+", value) if part)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _skip_path(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)
