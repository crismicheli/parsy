# parsy

`parsy` is a Python-first repository symbol graph generator. It accepts a public Git repository URL or local path, walks the real filesystem, parses Python source files with `ast`, builds a symbol table, resolves imports and aliases where practical, constructs a default property graph, and exports it.

The default export is JSON. Optional exporters include NetworkX, GraphML, Neo4j CSV, and PlantUML. A separate optional overview layer can save a high-level Mermaid diagram and render it to PNG if a Mermaid CLI-compatible renderer is available.

## Install

```bash
pip install -e ".[dev,networkx]"
```

## Quick start

Analyze a local repository:

```bash
parsy analyze ./some-python-repo --out outputs/some-python-repo
```

Analyze a public repository:

```bash
parsy analyze https://github.com/org/repo --out outputs/org-repo
```

Choose formats:

```bash
parsy analyze https://github.com/org/repo --format json --format graphml --format neo4j
```

Export PlantUML:

```bash
parsy analyze https://github.com/org/repo --format json --format plantuml
```

Generate a high-level Mermaid overview separately from the main symbol graph:

```bash
parsy analyze https://github.com/org/repo --overview --overview-png
```

Analyze several repositories from CLI arguments:

```bash
parsy analyze-many \
  https://github.com/org/repo-a \
  https://github.com/org/repo-b \
  --out outputs/batch \
  --format json --format plantuml
```

Analyze several repositories from a newline-delimited file:

```bash
parsy analyze-list repos.txt --out outputs/batch --format json
```

`repos.txt` can contain public Git URLs or local paths. Blank lines and lines starting with `#` are ignored. Batch commands write one output directory per source under `--out`.

## Default graph schema

Nodes:

- `Repository`
- `Package`
- `Module`
- `Class`
- `Function`
- `Method`
- `ExternalSymbol`

Edges:

- `CONTAINS`
- `IMPORTS`
- `ALIASES`
- `INHERITS`
- `CALLS`
- `DECORATES`
- `ANNOTATES_WITH`

Every node and edge carries a `properties` object so the model remains schema-extensible.

## Status

This is an MVP. Python support is implemented. TS/JS support is intentionally stubbed for a future `ts-morph` adapter.

## PlantUML export

PlantUML is a visualization projection over the canonical property graph. `INHERITS` maps to `<|--`; `CALLS`, `IMPORTS`, `ALIASES`, `DECORATES`, and `ANNOTATES_WITH` map to dependency arrows. Modules become packages, classes become classes, methods become class members, top-level functions become `<<function>>` classes, and unresolved imports or calls become `<<external>>` symbols.
