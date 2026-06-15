# Product Roadmap

## Phase 1: MVP

The smallest end-to-end useful release: **drift detection (`lg2m check`) for
LangGraph**. This is the spine of the plan — introspection + annotations +
generated Model-A routing reconciled against a Markdown contract — minus
scaffolding and the second framework.

Must-haves:

- `ir.py` — the intermediate representation (Graph/Node/Edge/Predicate/Route/
  DataModel/Attribute/Meta/Diagnostic/SourceLocation).
- `config/loader.py` — `[tool.lg2m]` / `lg2m.toml` graph configuration.
- `parsing/{mermaid,markdown,tables,meta}.py` — the owned `stateDiagram-v2`
  parser/emitter (`[else]`, `<<fork>>` / `<<join>>`, composite states) plus the
  Markdown contract, GFM tables, and the three metadata mechanisms.
- `annotations/{decorators,router,registry,reader}.py` — `@node` / `@predicate`
  / `@state_model` / `@data_model`, `lg2m.router(...)` with the generated
  `path_fn` + owned `path_map`, and the AST reader for `file:line`.
- `introspect/{base,langgraph_adapter,loader}.py` — the only framework-importing
  code, behind the `[langgraph]` extra; `get_graph()` + `state_schema` ->
  topology IR.
- `diff/engine.py` + `report/*` — three-way reconciliation (topology vs
  annotations vs diagram) into a `DriftReport`, text + JSON output, non-zero exit
  on any ERROR.
- `cli.py` (Typer) — `init`, `list`, `validate`, `check`.

Success criteria: the `examples/support_pipeline` fixture checks clean; a
routing-drifted copy returns non-zero with both locations; `check` writes
nothing.

## Phase 2: Post-Launch

- **Scaffolding (`gen`).** `lg2m gen --from-doc` (Markdown -> annotated code,
  including a `@predicate` stub per diagram label and a `lg2m.router` mapping)
  and `gen --from-code` (introspection + annotations -> Markdown skeleton).
  Golden round-trips both directions.
- **LangChain LCEL slice.** Emit the same Model-A mapping as a `RunnableBranch`;
  `gen --framework langchain`. Full fidelity stays LangGraph-only; LangChain
  covers linear chains + `RunnableBranch`.
- **CI version matrix.** Run the `@pytest.mark.langgraph` suite across a
  supported range of LangGraph / langchain-core versions so an upstream `Node` /
  `Edge` / `get_graph()` shape change surfaces as a test failure, not a user bug
  report.

## Future (post-v2)

- **Prose sync (`lg2m sync`).** A write-only verb with a `.lg2m.lock`
  per-entity baseline-hash store and a 3-way merge / conflict policy, syncing
  only the free-prose slice (docstrings <-> Markdown) for nodes and predicates;
  edges stay Markdown-only. Out of scope for v1, which only *reports*
  `PROSE_DRIFT`. Design note: `docs/prose-sync.md`.
