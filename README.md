# parsy

`parsy` is a Python-first repository symbol graph generator. It accepts a public Git repository URL or local path, walks the real filesystem, parses Python source files with `ast`, builds a symbol table, resolves imports and aliases where practical, constructs a default property graph, and exports it.

The default export is JSON. Optional exporters include NetworkX, GraphML, Neo4j CSV, and PlantUML. A separate optional overview layer can save a high-level Mermaid diagram and render it to PNG if Mermaid CLI is installed.

## Install

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
OR
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install `parsy` in editable mode:

```bash
pip install -e ".[dev,networkx]"
```

Check that the CLI is available:

```bash
parsy --help
```

## Optional Mermaid PNG support

`parsy` can save Mermaid source files without extra dependencies. However, PNG rendering requires the external Mermaid CLI command `mmdc`.

Install Mermaid CLI manually with npm:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Check that it is installed:

```bash
mmdc --version
```

If `mmdc` is not installed, `parsy --overview` still writes:

```text
overview/overview.mmd
```

but `--overview-png` will not create:

```text
overview/overview.png
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
parsy analyze https://github.com/org/repo \
  --format json \
  --format graphml \
  --format neo4j
```

Export PlantUML:

```bash
parsy analyze https://github.com/org/repo \
  --format json \
  --format plantuml
```

Generate a high-level Mermaid overview separately from the main symbol graph:

```bash
parsy analyze https://github.com/org/repo \
  --overview
```

Generate Mermaid overview plus PNG, if `mmdc` is installed:

```bash
parsy analyze https://github.com/org/repo \
  --overview \
  --overview-png
```

## Granularity

`parsy` supports three graph detail levels:

```text
low
medium
high
```

The default is:

```text
medium
```

### Low granularity

Low granularity keeps the graph compact.

```bash
parsy analyze https://github.com/org/repo \
  --granularity low \
  --format json \
  --verbose
```

Typical contents:

- Repository
- Modules
- Classes
- Functions
- Methods
- Containment edges
- Import edges
- Inheritance edges

It omits most call edges and external symbols.

### Medium granularity

Medium granularity is the default. It includes useful internal call information while avoiding many noisy unresolved external calls and annotation edges.

```bash
parsy analyze https://github.com/org/repo \
  --granularity medium \
  --format json \
  --format plantuml \
  --verbose
```

### High granularity

High granularity is the most detailed mode.

```bash
parsy analyze https://github.com/org/repo \
  --granularity high \
  --format json \
  --verbose
```

It includes decorators, annotations, and unresolved external call symbols. This can create very large graphs.

## Verbose mode

Use `--verbose` or `-v` to print high-level pipeline progress:

```bash
parsy analyze https://github.com/org/repo \
  --granularity medium \
  --format json \
  --verbose
```

Example progress messages:

```text
[parsy] Preparing repository: https://github.com/org/repo
[parsy] Walking python files under: .parsy-work/github-com-org-repo
[parsy] Selected 123 files for analysis
[parsy] Parsing source files
[parsy] Building symbol table
[parsy] Building graph with granularity=medium
[parsy] Exporting graph formats: json
[parsy] Analysis complete
```

## Batch analysis

Analyze several repositories from CLI arguments:

```bash
parsy analyze-many \
  https://github.com/org/repo-a \
  https://github.com/org/repo-b \
  --out outputs/batch \
  --format json \
  --format plantuml
```

Analyze several repositories from a newline-delimited file:

```bash
parsy analyze-list repos.txt \
  --out outputs/batch \
  --format json
```

Example `repos.txt`:

```text
# comments are ignored
https://github.com/org/repo-a
https://github.com/org/repo-b
./local-repo
```

Blank lines and lines starting with `#` are ignored. Batch commands write one output directory per source under `--out`.

## Default graph schema

Nodes:

- `Repository`
- `Module`
- `Class`
- `Function`
- `Method`
- `AliasSymbol`
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

## Output files

Default output:

```text
graph.json
symbol_inventory.json
```

Optional output files:

```text
graph.puml
graph.graphml
graph.networkx.pkl
neo4j/
overview/overview.mmd
overview/overview.png
```

`symbol_inventory.json` summarizes internal and external symbols by type, edge counts, and example symbols.

## PlantUML export

PlantUML is a visualization projection over the canonical property graph. `INHERITS` maps to `<|--`; `CALLS`, `IMPORTS`, `ALIASES`, `DECORATES`, and `ANNOTATES_WITH` map to dependency arrows. Modules become packages, classes become classes, methods become class members, top-level functions become `<<function>>` classes, and unresolved imports or calls become `<<external>>` symbols.

Example:

```bash
parsy analyze https://github.com/org/repo \
  --format plantuml
```

Output:

```text
graph.puml
```

## GitDiagram-compatible overview

The overview feature is separate from the main symbol graph. It does not affect `graph.json`.

Without an endpoint, `parsy` emits a simple deterministic Mermaid overview based on the walked files.

With a GitDiagram-compatible endpoint:

```bash
parsy analyze https://github.com/org/repo \
  --overview \
  --overview-endpoint https://your-endpoint.example.com
```

The endpoint should accept:

```json
{"source": "https://github.com/org/repo"}
```

and return either raw Mermaid text or JSON with:

```json
{"mermaid": "flowchart TD\n..."}
```

## Status

This is an MVP. Python support is implemented. TS/JS support is intentionally stubbed for a future `ts-morph` adapter.
