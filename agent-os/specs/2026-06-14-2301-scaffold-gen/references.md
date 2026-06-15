# References for Scaffold + `gen`

Exact wiring this layer reuses. Do not re-derive these; import and call them.

## Doc side (`--from-doc` input, both goldens' oracle)

- `src/lg2m/parsing/markdown.py` — `parse_markdown(text, *, file="<md>") -> MarkdownDoc`
  (frontmatter, `sections`, `entities`, `mermaid_lines`).
- `src/lg2m/diff/assemble.py` — `assemble_doc_model(doc, *, file="<md>") -> GraphModel(origin="markdown")`
  (populates `nodes`, `edges`, `routes`, `predicates`, `models`, `state_model_name`, `meta`).

## Code side (`--from-code`, reuses the `check` chain in `pipeline.py`)

- `src/lg2m/discovery/resolve.py` — `resolve(cfg, *, base_dir, graph_id) -> ResolvedGraph`
  (`module`, `attr`, `markdown_path`, `sys_paths`, `xray`, `framework`); raises `ConfigError`.
- `src/lg2m/introspect/loader.py` — `load_compiled(resolved) -> LoadedGraph(.compiled, .diagnostics)`
  (catches untrusted-code import failure as a diagnostic; `compiled is None` on failure).
- `src/lg2m/introspect/langgraph_adapter.py` — `LangGraphIntrospector(compiled, *, xray=, registry=)`
  `.introspect(graph_id) -> GraphModel(origin="code")`. **Import lazily.**
- `src/lg2m/pipeline.py` — `gather_annotations(package_dir) -> (Registry, locations)` (AST reader,
  never imports the target); the `check()` function shows the exact chaining to mirror.
- `src/lg2m/diff/assemble.py` — `assemble_code_model(topology, registry, locations) -> GraphModel(origin="code")`.

## Emitter primitives (reuse; do not hand-roll)

- `src/lg2m/parsing/tables.py` — `emit_table(headers: list[str], rows: list[dict[str, str]]) -> list[str]`
  (GFM tables with `\|` escaping) for the Index / Data Models / Edges tables.
- `src/lg2m/parsing/mermaid.py` — `emit_mermaid(diagram: MermaidDiagram) -> list[str]`, plus the
  shapes to build: `MermaidDiagram(states, edges)`, `MermaidState(id, is_subgraph, pseudostate, parent)`,
  `MermaidEdge(src, dst, predicate, conditional, is_else, scope)`.

## Authoring API the generated code targets

- `src/lg2m/annotations/router.py` — `router(source: str, branches: list[tuple[Any, str]]) -> Router`
  (`.path_map` keyed by predicate name + `ELSE_LABEL`); `ELSE` sentinel; rejects missing `[else]`
  and a predicate literally named `[else]`.
- `src/lg2m/annotations/decorators.py` — `node(node_id)`, `predicate(name)`, bare `state_model`,
  bare `data_model`.
- `src/lg2m/ir.py` — `Node`, `Edge`, `Route`, `Predicate`, `DataModel`, `Attribute`, `GraphModel`,
  `NodeKind {NODE, START, END}`, `ELSE_LABEL = "[else]"`.

## CLI to mirror

- `src/lg2m/cli.py` — `_resolve_config`, `_load_graphs`, `_resolve_graph_id`, `_fail` (exit 2),
  `OutputFormat`, the module-level `typer.Option(...)` constants (ruff B008 pattern), and
  `init`'s refuse-to-overwrite policy. Exit codes: 0 clean / 1 drift-or-structural / 2 usage-or-config.

## Example to match exactly

- `examples/support_pipeline/src/support_pipeline/` — `graph.py` (`build_graph()` wiring,
  `add_conditional_edges(source, route_fn, route_fn.path_map)`), `nodes.py` (`@node` stubs),
  `predicates.py` (`@predicate` stubs), `routing.py` (`lg2m.router(...)` mapping), `state.py`
  (`@state_model`/`@data_model`, `Annotated[...]` reducers), `__init__.py` (exports `build_graph`).
- `examples/support_pipeline/docs/support_pipeline.md` — the contract: frontmatter, `## Index`,
  `## Graph` (mermaid), `## Data Models`, `## Predicates`, `## Nodes`, `## Edges`.

## Design of record

docs/design.md Sections 10 (scaffolding), 11 (CLI), 12 (limitations, prose-sync out of scope),
13 (build order item 5), 14 (test strategy: golden round-trips). Prior spec:
`agent-os/specs/2026-06-14-2225-cli-typer/` (Layer 4, the CLI).
