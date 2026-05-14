from __future__ import annotations

from parsy.parse.python.parser import PythonAstParser


def parser_for_language(language: str):
    if language == "python":
        return PythonAstParser()
    if language in {"typescript", "javascript"}:
        raise NotImplementedError("TS/JS parsing is planned via a future ts-morph adapter.")
    raise ValueError(f"Unsupported language: {language}")

