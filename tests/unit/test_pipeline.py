from __future__ import annotations

import json
from pathlib import Path

import pytest

from parsy.config import ParsyConfig
from parsy.config.models import ExportConfig
from parsy.exporters.graphml_exporter import export_graphml
from parsy.graph.models import Edge, Node, PropertyGraph
from parsy.pipeline import analyze, analyze_many, read_sources_file


def test_pipeline_exports_json(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"
    out = tmp_path / "out"
    result = analyze(str(fixture), out_dir=out, config=ParsyConfig())
    assert result.files_analyzed == 3
    graph_path = out / "graph.json"
    assert graph_path.exists()
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in data["nodes"]}
    edge_kinds = {edge["kind"] for edge in data["edges"]}
    assert "pkg.models.Animal" in node_ids
    assert "pkg.models.Dog" in node_ids
    assert "INHERITS" in edge_kinds
    assert "CALLS" not in edge_kinds


def test_pipeline_medium_granularity_includes_calls(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"
    out = tmp_path / "out"
    cfg = ParsyConfig()
    cfg.schema.granularity = "medium"
    cfg.schema.apply_granularity()
    analyze(str(fixture), out_dir=out, config=cfg)
    graph_path = out / "graph.json"
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    edge_kinds = {edge["kind"] for edge in data["edges"]}
    assert "CALLS" in edge_kinds


def test_function_view_exports_call_dependencies_only(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"
    out = tmp_path / "out"
    cfg = ParsyConfig()
    cfg.schema.granularity = "medium"
    cfg.schema.view = "function"
    cfg.schema.apply_granularity()
    analyze(str(fixture), out_dir=out, config=cfg)
    graph_path = out / "graph.json"
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    node_kinds = {node["kind"] for node in data["nodes"]}
    edge_kinds = {edge["kind"] for edge in data["edges"]}
    assert node_kinds <= {"Function", "Method", "ExternalSymbol"}
    assert edge_kinds <= {"CALLS"}
    assert "CALLS" in edge_kinds


def test_projection_views_change_saved_graph(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"

    class_cfg = ParsyConfig()
    class_cfg.schema.view = "class"
    class_cfg.schema.apply_granularity()
    analyze(str(fixture), out_dir=tmp_path / "class", config=class_cfg)

    module_cfg = ParsyConfig()
    module_cfg.schema.view = "module"
    module_cfg.schema.apply_granularity()
    analyze(str(fixture), out_dir=tmp_path / "module", config=module_cfg)

    class_graph = json.loads((tmp_path / "class" / "graph.json").read_text(encoding="utf-8"))
    module_graph = json.loads((tmp_path / "module" / "graph.json").read_text(encoding="utf-8"))

    assert {node["kind"] for node in class_graph["nodes"]} == {"Class", "Module"}
    assert {node["kind"] for node in module_graph["nodes"]} == {"Module"}
    assert len(class_graph["nodes"]) > len(module_graph["nodes"])


def test_existing_output_directory_requires_overwrite(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"
    out = tmp_path / "out"
    out.mkdir()
    (out / "existing.txt").write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(FileExistsError):
        analyze(str(fixture), out_dir=out, config=ParsyConfig())

    cfg = ParsyConfig()
    cfg.exports.overwrite = True
    analyze(str(fixture), out_dir=out, config=cfg)
    assert (out / "graph.json").exists()
    assert (out / "existing.txt").read_text(encoding="utf-8") == "do not overwrite"


def test_pipeline_exports_plantuml(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"
    out = tmp_path / "out"
    cfg = ParsyConfig(exports=ExportConfig(formats=["plantuml"]))
    analyze(str(fixture), out_dir=out, config=cfg)
    puml = out / "graph.puml"
    assert puml.exists()
    text = puml.read_text(encoding="utf-8")
    assert "@startuml" in text
    assert "Animal" in text
    assert "<|--" in text


def test_graphml_export_uses_unique_edge_ids(tmp_path: Path) -> None:
    graph = PropertyGraph()
    graph.add_node(Node(id="a", kind="Module", label="a"))
    graph.add_node(Node(id="b", kind="Function", label="b"))
    graph.add_node(Node(id="c", kind="Function", label="c"))
    graph.add_edge(Edge(source="a", target="b", kind="IMPORTS"))
    graph.add_edge(Edge(source="a", target="c", kind="IMPORTS"))
    graph.add_edge(Edge(source="a", target="b", kind="CALLS"))

    path = export_graphml(graph, tmp_path / "graph.graphml")
    text = path.read_text(encoding="utf-8")

    assert 'id="e_0_' in text
    assert 'id="e_1_' in text
    assert 'id="e_2_' in text


def test_analyze_many_writes_one_directory_per_source(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "python_sample"
    out = tmp_path / "batch"
    batch = analyze_many([str(fixture), str(fixture)], out_dir=out, config=ParsyConfig())
    assert len(batch.items) == 2
    assert batch.total_files_analyzed == 6
    assert batch.items[0].out_dir != batch.items[1].out_dir
    assert (batch.items[0].out_dir / "graph.json").exists()
    assert (batch.items[1].out_dir / "graph.json").exists()


def test_read_sources_file_ignores_comments_and_blanks(tmp_path: Path) -> None:
    sources_file = tmp_path / "repos.txt"
    sources_file.write_text("\n# comment\nhttps://github.com/a/b\n\n./local\n", encoding="utf-8")
    assert read_sources_file(sources_file) == ["https://github.com/a/b", "./local"]
