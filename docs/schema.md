# Default Python Schema

`parsy` uses a property graph:

```text
Node(id, kind, label, properties)
Edge(source, target, kind, properties)
```

Default node kinds:

- Repository
- Module
- Class
- Function
- Method
- ExternalSymbol

Default edge kinds:

- CONTAINS
- IMPORTS
- ALIASES
- INHERITS
- CALLS
- DECORATES
- ANNOTATES_WITH

Edges include `resolution_status` and `confidence` where resolution is uncertain.

## PlantUML projection

The PlantUML exporter writes `graph.puml`.

Mapping:

- `Module` -> `package`
- `Class` -> `class`
- `Method` -> class member
- `Function` -> `class <<function>>`
- `AliasSymbol` -> `class <<alias>>`
- `ExternalSymbol` -> `class <<external>>`
- `INHERITS` -> `<|--`
- `IMPORTS`, `CALLS`, `ALIASES`, `DECORATES`, `ANNOTATES_WITH` -> dependency arrows

The JSON graph remains the canonical export for downstream analysis.
