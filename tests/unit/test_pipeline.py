from __future__ import annotations

import json
from pathlib import Path

from parsy.config import ParsyConfig
from parsy.config.models import ExportConfig
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
    assert "CALLS" in edge_kinds


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
