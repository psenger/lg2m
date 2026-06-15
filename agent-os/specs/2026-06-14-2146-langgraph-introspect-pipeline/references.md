# References — lg2m layer 3

## The real `get_graph` shape (the adapter's target)

- `examples/support_pipeline_native/introspect.py` — dumps `compiled.get_graph(xray=True)`: iterates
  `g.nodes` (ids) and `g.edges` (`.source`/`.target`/`.conditional`/`.data`), and reads the state
  schema with `typing.get_type_hints(StateSchema, include_extras=True)` + `Annotated.__metadata__`
  reducers. Its README has the expected printed output (14 nodes, 16 edges, the reducer table).
- `examples/support_pipeline_native/langgraph_app.py` — the native StateGraph wiring (add_node,
  add_edge, add_conditional_edges, `destinations=`, the `investigate` subgraph compile). NOTE: its
  conditional `path_map` uses **target-named** keys, so its edge labels are NOT predicate names —
  unlike the lg2m-annotated graph. Do not use it to infer the Model-A label semantics.

## The graph under test (what `check` actually introspects)

- `examples/support_pipeline/src/support_pipeline/graph.py` — the lg2m-annotated `build_graph()`;
  uses `add_conditional_edges("classify_intent", route_after_classify, route_after_classify.path_map)`
  where `path_map` is keyed by **predicate name** (Model A). This is the graph the adapter reads.
- `examples/support_pipeline/src/support_pipeline/{state,routing,predicates,nodes}.py` — the
  annotated source the loader imports (populating the registry) and the reader locates.
- `examples/support_pipeline/lg2m.toml` — `graph = "support_pipeline.graph:build_graph"`,
  `markdown = "docs/support_pipeline.md"`, `sys_path = ["src"]`, `xray = true`.

## Layer-1/2 code reused

- `src/lg2m/config/loader.py` — `load(path) -> dict[str, dict]` (the `[tool.lg2m.graphs.*]` mapping).
- `src/lg2m/annotations/{registry,reader}.py` — the live registry (populated on import) and
  `read_file` / `merge_locations` for `file:line`.
- `src/lg2m/diff/assemble.py` — `assemble_code_model(topology, registry, locations)` (consumes the
  adapter's `GraphModel` unchanged) and `_CONDITIONAL_KINDS` (the Command-edge fix).
- `src/lg2m/diff/engine.py` — `reconcile`. `tests/_oracle.py` — the Fake authored to match the real
  adapter; `tests/test_assemble.py` — the canonical node/edge constants reused by the adapter tests.

## Design of record

- `docs/design.md` Section 2 (what the frameworks expose), Section 4 (the three sources), Section 5 (package
  layout: `introspect/langgraph_adapter.py`, `discovery/resolve.py`, `introspect/loader.py`),
  Section 11 (CLI surface — the layer this one precedes), Section 12 (limitations: name-level
  reducers, untrusted user code, xray nesting cap).
- The approved implementation plan: `~/.claude/plans/continue-lg2m-layer-2b-idempotent-cake.md`.
