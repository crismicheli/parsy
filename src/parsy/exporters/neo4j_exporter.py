from __future__ import annotations

import csv
from pathlib import Path

from parsy.graph.models import PropertyGraph


def export_neo4j(graph: PropertyGraph, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "nodes.csv"
    edges_path = output_dir / "edges.csv"
    with nodes_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id:ID", ":LABEL", "label", "properties"])
        writer.writeheader()
        for node in graph.nodes.values():
            writer.writerow(
                {
                    "id:ID": node.id,
                    ":LABEL": node.kind,
                    "label": node.label,
                    "properties": str(node.properties),
                }
            )
    with edges_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[":START_ID", ":END_ID", ":TYPE", "properties"])
        writer.writeheader()
        for edge in graph.edges:
            writer.writerow(
                {
                    ":START_ID": edge.source,
                    ":END_ID": edge.target,
                    ":TYPE": edge.kind,
                    "properties": str(edge.properties),
                }
            )
    loader = output_dir / "load.cypher"
    loader.write_text(
        "\n".join(
            [
                "// Example Neo4j import commands; adjust paths for your environment.",
                "LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row",
                "CALL { WITH row",
                "  CREATE (n) SET n.id = row.`id:ID`, n.label = row.label, n.properties = row.properties",
                "} IN TRANSACTIONS;",
                "LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row",
                "CALL { WITH row",
                "  MATCH (a {id: row.`:START_ID`}), (b {id: row.`:END_ID`})",
                "  CREATE (a)-[r:RELATED {kind: row.`:TYPE`, properties: row.properties}]->(b)",
                "} IN TRANSACTIONS;",
            ]
        ),
        encoding="utf-8",
    )
    return output_dir

