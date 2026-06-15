# Changelog

All notable changes to `langgraph-to-from-mermaid` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-06-15

Initial release. All six layers of the design (`docs/design.md` Section 13) are
shipped and green: the intermediate representation, the config loader, the parsers,
the annotation decorators and router, the diff and report engine, the real LangGraph
introspector, the Typer CLI, code/contract generation, and prose sync.

### Added

#### Intermediate Representation (`ir.py`)

- `GraphModel`, `Node`, `Edge`, `Predicate`, `Route`, `DataModel`, `Attribute`,
  `Meta`, `Diagnostic`, and `SourceLocation` — all frozen dataclasses with
  structural identity (identity fields drive equality/hashing; all other fields are
  `field(compare=False)`).
- `ELSE_LABEL = "[else]"` — the single shared literal for the required default
  branch, used by the Mermaid parser, the router, and the decorators.

#### Config loader (`config/loader.py`)

- `[tool.lg2m.graphs.<id>]` section in `pyproject.toml` or a standalone
  `lg2m.toml`; fields: `graph`, `markdown`, `sys_path`, `xray`, `framework`.
- Uses stdlib `tomllib` on Python 3.11+; falls back to `tomli` on 3.10.

#### Mermaid parser/emitter (`parsing/mermaid.py`)

- Full `stateDiagram-v2` parse and emit: unconditional transitions, conditional
  transitions (`:predicate_name`), the reserved `[else]` default, `<<fork>>` /
  `<<join>>` pseudostates, composite (nested) states, and `[*]` entry/exit.
- Round-trip contract is structural, not byte-exact: `parse(emit(parse(x)))`
  preserves edge order and nesting.
- No third-party Mermaid library; `lg2m` owns this parser.

#### Markdown contract parser (`parsing/markdown.py`, `parsing/tables.py`, `parsing/meta.py`)

- Forward line scanner over the contract document: frontmatter (`lg2m_graph: <id>`),
  `## Graph` mermaid block, `## Data Models` GFM tables, `## Predicates` /
  `## Nodes` / `## Edges` sections with per-entity prose.
- GFM table parser with `\|` escaping for Data Model and Index tables.
- Three metadata mechanisms, all parsed and emitted:
  - Visible key/value table (`| meta | value |`) — drift-checked.
  - Hidden machine fence (`<!-- lg2m: key=value -->`) — drift-checked.
  - Free-text blockquote (`> Note: ...`) — human prose, not checked.

#### Annotations (`annotations/`)

- `@node("id")` — links a function to a diagram state and its prose section;
  records `SourceLocation`; returns the wrapped callable unchanged.
- `@predicate("name")` — marks a whole leaf condition; returns unchanged.
- `@state_model` / `@data_model` — link state and data model classes to their
  Markdown sections; return unchanged.
- `lg2m.router(source, branches)` — factory that accepts an ordered
  `[(predicate_name, target), ..., (ELSE, target)]` mapping and returns a
  generated `path_fn`. Owns the `path_map` (keyed by predicate name so
  `get_graph()` reports each conditional edge's label as its predicate name).
  Rejects a missing `[else]` and a predicate literally named `[else]`.
- `lg2m.ELSE` — sentinel for the required default branch.
- Module-level registry (reset between graphs and between tests via the autouse
  `reset_registry` fixture).
- AST reader (`annotations/reader.py`) — recovers `file:line` without importing
  user modules; `merge_locations` joins the reader's locations with the registry.

#### LangGraph introspector (`introspect/`, behind `[langgraph]` extra)

- `langgraph_adapter.py` — the only file that imports `langgraph` /
  `langchain_core`; lazy-loaded by `pipeline.py` so `import lg2m.pipeline` stays
  framework-free.
- Reads `compiled.get_graph(xray=True)` for nodes, edges, conditional flags,
  `path_map` targets, and `compiled.builder.state_schema` for the state schema
  with reducers (`add_messages`, `operator.add`, custom).
- `FakeIntrospector` for framework-free tests.
- `loader.py` — imports a user module by `"mod:attr"` string, runs the factory,
  and surfaces import errors with `SourceLocation`.

#### Diff engine and reports (`diff/`, `report/`)

- Three-way reconciliation: topology (introspection) vs annotations vs diagram.
- Drift categories: `NODE_MISSING_IN_DOC` / `_IN_CODE`, `ANNOTATION_NODE_MISMATCH`,
  `PROSE_DRIFT`, `EDGE_MISSING_*`, `EDGE_CONDITIONALITY_MISMATCH`,
  `ROUTE_TARGET_MISMATCH`, `ROUTER_NOT_WIRED`, `PREDICATE_UNDEFINED`,
  `MISSING_ELSE`, `EDGE_LABEL_MISMATCH`, `PREDICATE_MISSING_*`,
  `MODEL_MISSING_*`, `ATTR_*`, `ATTR_TYPE_DRIFT`, `ATTR_REDUCER_DRIFT`,
  `STATE_MODEL_MISMATCH`, `META_DRIFT`.
- Each `DriftItem` carries code and doc `file:line` plus a hint.
- Text renderer (`report/text.py`) and JSON renderer (`report/json.py`).
- `check` exits non-zero on any ERROR.

#### CLI (`cli.py`, Typer)

- `lg2m init` — scaffold a starter `lg2m.toml`.
- `lg2m list` — list the configured graphs.
- `lg2m validate` — each side parses, the entry point imports, one state model
  per graph, every fan-out has an `[else]`.
- `lg2m check [--format text|json] [--strict] [--no-prose]` — full three-way
  reconciliation; writes nothing.
- `lg2m gen --from-doc [--out PATH]` — Markdown contract → annotated LangGraph
  code: `@state_model` / `@data_model`, `@node` stubs, a `@predicate` stub per
  diagram label, a `lg2m.router(...)` mapping built from the conditional labels,
  and a complete `build_graph()`. `--out` writes files and refuses to overwrite;
  without it the output is a stdout dry-run.
- `lg2m gen --from-code [--out PATH]` — introspection + annotations → Markdown
  skeleton: conditional labels from the router mapping, metadata for
  non-topological facts, existing prose preserved, absent prose as `TODO`.
- `lg2m sync [--prefer code|doc] [--dry-run]` — prose write-back; see below.
- Exit codes: `0` clean, `1` drift or structural error, `2` usage or config error.
- `[project.scripts]` entry wires `lg2m` onto `PATH` after install.

#### Scaffolding (`scaffold/`)

- `gen --from-doc` round-trips the topological core faithfully: nodes, edges,
  conditional routers with `[else]`, parallel fork/join, state model and reducers.
  Subgraphs, `Send`, and `Command` are left as `# TODO` (see Limitations).
- `gen --from-code` emits canonical flat Mermaid; flattened subgraph `parent:child`
  ids are sanitised to valid Python identifiers while preserving the
  `@node("parent:child")` string.
- Round-trip golden tests cover both directions on a subgraph-free fixture and a
  lenient smoke test on the richer example.

#### Prose sync (`sync/`)

- `lg2m sync` — write-only verb that synchronises the free-prose slice (docstrings
  in code ↔ prose sections in Markdown) for nodes and predicates. Edges stay
  Markdown-only (no docstring home in a router mapping or `add_edge` call).
- `.lg2m.lock` — a committed TOML lockfile of per-entity baseline hashes; drives
  the four-case decision per entity:
  - Only Markdown changed → write into the docstring.
  - Only code changed → write into the Markdown.
  - Both changed → conflict; refuse and show diff (or honour `--prefer code|doc`).
  - Neither changed → no-op.
- `sync/merge.py` — 3-way merge at entity granularity.
- `--dry-run` — shows what would change without writing.
- Structured metadata (introspection-owned) and `> Note:` blocks are never written
  into docstrings.

#### Examples

- `examples/support_pipeline_native/` — the complete graph in both LangGraph
  (full surface) and LangChain (LCEL-expressible slice), with no `lg2m` dependency.
  Deterministic node bodies; no LLM calls or API keys required.
- `examples/support_pipeline/` — the same graph with `lg2m` annotations applied
  (`@node`, `@predicate`, `lg2m.router`, `@state_model`, `@data_model`) and a
  complete Mermaid + Markdown contract. Checks clean under `lg2m check`.

#### Test suite (`tests/`)

- 231 tests; enforces a 90% line-coverage gate on the `lg2m` package (current
  coverage ~96%).
- Framework-free suite requires only `.[dev]`; `@pytest.mark.langgraph` tests
  require `.[langgraph,dev]`.
- Autouse `reset_registry` fixture ensures the annotation registry is clean
  between tests.

### Limitations (v0.1.0)

- **LangChain `gen`** (`--framework langchain`) is not yet implemented; `gen`
  emits LangGraph only. The routing model (Model A) compiles to `RunnableBranch`
  by design; the emitter is on the roadmap.
- **Subgraph / `Send` / `Command` in `gen`**: `--from-doc` and `--from-code`
  round-trip the topological core faithfully for subgraph-free graphs. Flattened
  `parent:child` ids cannot be de-canonicalised back to composite-state sugar;
  `Send` / `Command` edges are left as `# TODO`. This is documented in
  `docs/design.md` Section 12.
- **`sync` baseline**: hash-only at entity granularity (no intra-paragraph 3-way
  merge). Raw / byte-prefixed docstring styles are refused.
- **Predicate internal logic** is never read or verified; only the predicate name
  and its presence in the registry are checked.
- **`Command` / `Send`** routes are invisible to introspection unless the node
  declares `add_node(..., destinations=...)`; without `destinations` they survive
  only as `> Note:`.
- **Subgraph nesting depth**: `xray` rendering has a known upstream bug at 3+
  nesting levels; `lg2m` documents and enforces a nesting-depth limit.
- **CI version matrix** across LangGraph / langchain-core releases is not yet
  wired up.

[0.1.0]: https://github.com/psenger/langgraph_to_from_mermaid/releases/tag/v0.1.0
