# Architecture

`parsy` intentionally separates high-level architecture overview generation from deterministic symbol graph generation.

```text
source URL/path
  -> repository preparation
  -> filesystem walk
  -> language parser
  -> symbol table
  -> graph builder
  -> exporters
```

The overview branch is optional:

```text
source URL/path
  -> GitDiagram-compatible Mermaid generation
  -> .mmd
  -> optional .png
```

The core graph pipeline does not depend on GitDiagram.

