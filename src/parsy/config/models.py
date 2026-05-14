from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class WalkConfig:
    include: list[str] = field(default_factory=lambda: ["**/*.py"])
    exclude: list[str] = field(
        default_factory=lambda: [
            "**/.git/**",
            "**/.venv/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/build/**",
            "**/dist/**",
        ]
    )


@dataclass(slots=True)
class SchemaConfig:
    name: str = "python-default"
    granularity: str = "low"
    view: str = "dependency"
    include_external_symbols: bool = True
    include_calls: bool = True
    include_decorators: bool = False
    include_annotations: bool = False
    include_unresolved_external_calls: bool = False

    def apply_granularity(self) -> None:
        if self.granularity == "low":
            self.include_external_symbols = False
            self.include_calls = False
            self.include_decorators = False
            self.include_annotations = False
            self.include_unresolved_external_calls = False
        elif self.granularity == "medium":
            self.include_external_symbols = True
            self.include_calls = True
            self.include_decorators = False
            self.include_annotations = False
            self.include_unresolved_external_calls = False
        elif self.granularity == "high":
            self.include_external_symbols = True
            self.include_calls = True
            self.include_decorators = True
            self.include_annotations = True
            self.include_unresolved_external_calls = True
        else:
            raise ValueError(f"Unknown granularity: {self.granularity}")

    def validate_view(self) -> None:
        valid_views = {"full", "dependency", "module", "class", "function"}
        if self.view not in valid_views:
            raise ValueError(f"Unknown view: {self.view}")


@dataclass(slots=True)
class ExportConfig:
    formats: list[str] = field(default_factory=lambda: ["json"])


@dataclass(slots=True)
class OverviewConfig:
    enabled: bool = False
    endpoint: str | None = None
    render_png: bool = False


@dataclass(slots=True)
class ParsyConfig:
    language: str = "python"
    work_dir: Path = Path(".parsy-work")
    walk: WalkConfig = field(default_factory=WalkConfig)
    schema: SchemaConfig = field(default_factory=SchemaConfig)
    exports: ExportConfig = field(default_factory=ExportConfig)
    overview: OverviewConfig = field(default_factory=OverviewConfig)
    verbose: bool = False

    @classmethod
    def from_file(cls, path: str | Path | None) -> "ParsyConfig":
        if path is None:
            cfg = cls()
            cfg.schema.apply_granularity()
            return cfg
        with Path(path).open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.from_mapping(raw)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "ParsyConfig":
        walk = WalkConfig(**raw.get("walk", {}))
        schema = SchemaConfig(**raw.get("schema", {}))
        schema.apply_granularity()
        schema.validate_view()
        exports = ExportConfig(**raw.get("exports", {}))
        overview = OverviewConfig(**raw.get("overview", {}))
        work_dir = Path(raw.get("work_dir", ".parsy-work"))
        return cls(
            language=raw.get("language", "python"),
            work_dir=work_dir,
            walk=walk,
            schema=schema,
            exports=exports,
            overview=overview,
            verbose=raw.get("verbose", False),
        )

    def with_cli_overrides(
        self,
        *,
        language: str | None = None,
        formats: tuple[str, ...] | list[str] | None = None,
        overview: bool | None = None,
        overview_endpoint: str | None = None,
        overview_png: bool | None = None,
        granularity: str | None = None,
        view: str | None = None,
        verbose: bool | None = None,
    ) -> "ParsyConfig":
        if language:
            self.language = language
        if formats:
            self.exports.formats = list(formats)
        if overview is not None:
            self.overview.enabled = overview
        if overview_endpoint:
            self.overview.endpoint = overview_endpoint
        if overview_png is not None:
            self.overview.render_png = overview_png
        if granularity:
            self.schema.granularity = granularity
        if view:
            self.schema.view = view
        if verbose is not None:
            self.verbose = verbose
        self.schema.apply_granularity()
        self.schema.validate_view()
        return self
