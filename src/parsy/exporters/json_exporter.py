from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parsy.graph.models import PropertyGraph


def export_json(graph: PropertyGraph, output_path: Path) -> Path:
    data: dict[str, Any] = {
        "nodes": [
            {
                "id": node.id,
                "kind": node.kind,
                "label": node.label,
                "properties": node.properties,
            }
            for node in graph.nodes.values()
        ],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "kind": edge.kind,
                "properties": edge.properties,
            }
            for edge in graph.edges
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path

