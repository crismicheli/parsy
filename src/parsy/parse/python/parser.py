from __future__ import annotations

import ast
from pathlib import Path

from parsy.parse.models import ClassFact, FunctionFact, ImportFact, ParsedFile
from parsy.utils.paths import module_name_from_path
from parsy.walk.records import FileRecord


class PythonAstParser:
    """Parse Python source into language facts using the standard ast module."""

    def parse_file(self, repo_root: Path, record: FileRecord) -> ParsedFile:
        source = record.path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(record.path))
        module_name = module_name_from_path(repo_root, record.path)
        visitor = _PythonFactVisitor(module_name)
        visitor.visit(tree)
        return ParsedFile(
            path=record.path,
            relative_path=record.relative_path,
            module_name=module_name,
            imports=visitor.imports,
            classes=visitor.classes,
            functions=visitor.functions,
            metadata={"language": "python"},
        )


class _PythonFactVisitor(ast.NodeVisitor):
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.scope_stack: list[str] = [module_name]
        self.class_depth = 0
        self.imports: list[ImportFact] = []
        self.classes: list[ClassFact] = []
        self.functions: list[FunctionFact] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportFact(module=alias.name, name=None, alias=alias.asname, level=0, line=node.lineno)
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.imports.append(
                ImportFact(
                    module=node.module,
                    name=alias.name,
                    alias=alias.asname,
                    level=node.level,
                    line=node.lineno,
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = f"{self.current_scope}.{node.name}"
        self.classes.append(
            ClassFact(
                name=node.name,
                qualified_name=qualified,
                bases=[expr_to_name(base) for base in node.bases],
                decorators=[expr_to_name(dec) for dec in node.decorator_list],
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", None),
                scope=self.current_scope,
            )
        )
        self.scope_stack.append(qualified)
        self.class_depth += 1
        self.generic_visit(node)
        self.class_depth -= 1
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualified = f"{self.current_scope}.{node.name}"
        calls = [expr_to_name(call.func) for call in ast.walk(node) if isinstance(call, ast.Call)]
        annotations = collect_annotations(node)
        self.functions.append(
            FunctionFact(
                name=node.name,
                qualified_name=qualified,
                decorators=[expr_to_name(dec) for dec in node.decorator_list],
                annotations=annotations,
                calls=[call for call in calls if call],
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", None),
                scope=self.current_scope,
                is_method=self.class_depth > 0,
            )
        )
        self.scope_stack.append(qualified)
        self.generic_visit(node)
        self.scope_stack.pop()

    @property
    def current_scope(self) -> str:
        return self.scope_stack[-1]


def expr_to_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = expr_to_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return expr_to_name(node.func)
    if isinstance(node, ast.Subscript):
        return expr_to_name(node.value)
    if isinstance(node, ast.Constant):
        return repr(node.value)
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def collect_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    annotations: list[str] = []
    args = list(node.args.args) + list(node.args.kwonlyargs)
    if node.args.vararg:
        args.append(node.args.vararg)
    if node.args.kwarg:
        args.append(node.args.kwarg)
    for arg in args:
        if arg.annotation is not None:
            annotations.append(expr_to_name(arg.annotation))
    if node.returns is not None:
        annotations.append(expr_to_name(node.returns))
    return [ann for ann in annotations if ann]

