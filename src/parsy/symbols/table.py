from __future__ import annotations

from dataclasses import dataclass, field

from parsy.parse.models import ParsedFile
from parsy.symbols.models import ImportAlias, Symbol


@dataclass(slots=True)
class SymbolTable:
    symbols: dict[str, Symbol] = field(default_factory=dict)
    imports_by_module: dict[str, list[ImportAlias]] = field(default_factory=dict)
    short_index: dict[str, list[str]] = field(default_factory=dict)

    def add(self, symbol: Symbol) -> None:
        self.symbols[symbol.id] = symbol
        self.short_index.setdefault(symbol.name, []).append(symbol.id)

    def add_import_alias(self, module_name: str, alias: ImportAlias) -> None:
        self.imports_by_module.setdefault(module_name, []).append(alias)

    def resolve_name(self, module_name: str, scope: str, name: str) -> tuple[str | None, str]:
        if not name:
            return None, "unresolved"
        if name in self.symbols:
            return name, "resolved"
        local_candidate = f"{scope}.{name}"
        if local_candidate in self.symbols:
            return local_candidate, "resolved"
        module_candidate = f"{module_name}.{name}"
        if module_candidate in self.symbols:
            return module_candidate, "resolved"
        first = name.split(".")[0]
        for alias in self.imports_by_module.get(module_name, []):
            if alias.local_name == first:
                suffix = name[len(first) :].lstrip(".")
                target = f"{alias.target}.{suffix}" if suffix else alias.target
                if target in self.symbols:
                    return target, "resolved"
                return target, "external"
        if name in self.short_index and len(self.short_index[name]) == 1:
            return self.short_index[name][0], "resolved"
        if name in self.short_index and len(self.short_index[name]) > 1:
            return None, "ambiguous"
        return name, "external"


def build_symbol_table(parsed_files: list[ParsedFile]) -> SymbolTable:
    table = SymbolTable()
    for parsed in parsed_files:
        table.add(
            Symbol(
                id=parsed.module_name,
                kind="Module",
                name=parsed.module_name.split(".")[-1] if parsed.module_name else "__root__",
                qualified_name=parsed.module_name,
                file_path=parsed.path,
                line_start=1,
                line_end=None,
                scope=None,
                properties={"relative_path": parsed.relative_path.as_posix(), "language": "python"},
            )
        )
        for cls in parsed.classes:
            table.add(
                Symbol(
                    id=cls.qualified_name,
                    kind="Class",
                    name=cls.name,
                    qualified_name=cls.qualified_name,
                    file_path=parsed.path,
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                    scope=cls.scope,
                )
            )
        for fn in parsed.functions:
            table.add(
                Symbol(
                    id=fn.qualified_name,
                    kind="Method" if fn.is_method else "Function",
                    name=fn.name,
                    qualified_name=fn.qualified_name,
                    file_path=parsed.path,
                    line_start=fn.line_start,
                    line_end=fn.line_end,
                    scope=fn.scope,
                )
            )
        for imp in parsed.imports:
            local_name = imp.alias or imp.name or (imp.module.split(".")[0] if imp.module else "")
            target = _import_target(parsed.module_name, imp.module, imp.name, imp.level)
            table.add_import_alias(
                parsed.module_name,
                ImportAlias(
                    local_name=local_name,
                    target=target,
                    source_module=imp.module,
                    line=imp.line,
                ),
            )
    return table


def _import_target(current_module: str, module: str | None, name: str | None, level: int) -> str:
    if level > 0:
        base_parts = current_module.split(".")[:-level]
        if module:
            base_parts.extend(module.split("."))
        if name and name != "*":
            base_parts.append(name)
        return ".".join(part for part in base_parts if part)
    parts: list[str] = []
    if module:
        parts.append(module)
    if name and name != "*":
        parts.append(name)
    return ".".join(parts)

