from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from parsy.graph.models import PropertyGraph


def export_symbol_inventory(graph: PropertyGraph, output_path: Path) -> Path:
    inventory = build_symbol_inventory(graph)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return output_path


def build_symbol_inventory(graph: PropertyGraph) -> dict[str, Any]:
    node_counts = {
        "internal": Counter(),
        "external": Counter(),
        "all": Counter(),
    }

    node_examples = {
        "internal": defaultdict(list),
        "external": defaultdict(list),
    }

    for node in graph.nodes.values():
        group = "external" if node.kind == "ExternalSymbol" else "internal"
        node_counts[group][node.kind] += 1
        node_counts["all"][node.kind] += 1

        if len(node_examples[group][node.kind]) < 25:
            node_examples[group][node.kind].append(
                {
                    "id": node.id,
                    "kind": node.kind,
                    "label": node.label,
                    "qualified_name": node.properties.get("qualified_name"),
                    "file_path": node.properties.get("file_path"),
                    "line_start": node.properties.get("line_start"),
                    "line_end": node.properties.get("line_end"),
                }
            )

    edge_counts = Counter(edge.kind for edge in graph.edges)

    external_symbols_by_prefix = Counter()
    for node in graph.nodes.values():
        if node.kind != "ExternalSymbol":
            continue
        prefix = node.id.split(".")[0] if node.id else ""
        external_symbols_by_prefix[prefix] += 1

    return {
        "node_counts": {
            group: dict(counter)
            for group, counter in node_counts.items()
        },
        "edge_counts": dict(edge_counts),
        "external_symbols_by_prefix": dict(external_symbols_by_prefix),
        "examples": {
            group: dict(values)
            for group, values in node_examples.items()
        },
    }
