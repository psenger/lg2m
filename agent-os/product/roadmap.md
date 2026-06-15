# Product Roadmap

## v0.1.0 (shipped)

All layers built and green. The full build order from `docs/design.md` Section 13
is complete:

- `ir.py` — the intermediate representation.
- `config/loader.py` — `[tool.lg2m]` / `lg2m.toml` graph configuration.
- `parsing/{mermaid,markdown,tables,meta}.py` — the owned `stateDiagram-v2`
  parser/emitter plus the Markdown contract, GFM tables, and the three metadata
  mechanisms.
- `annotations/{decorators,router,registry,reader}.py` — `@node` / `@predicate`
  / `@state_model` / `@data_model`, `lg2m.router(...)` with the generated
  `path_fn` + owned `path_map`, and the AST reader for `file:line`.
- `introspect/{base,langgraph_adapter,loader}.py` — the only framework-importing
  code, behind the `[langgraph]` extra; `get_graph()` + `state_schema` ->
  topology IR.
- `diff/engine.py` + `report/*` — three-way reconciliation (topology vs
  annotations vs diagram) into a `DriftReport`, text + JSON output, non-zero exit
  on any ERROR.
- `cli.py` (Typer) — `init`, `list`, `validate`, `check`, `gen`, `sync`.
- `scaffold/*` (`gen` verb) — `gen --from-doc` (Markdown -> annotated code) and
  `gen --from-code` (introspection + annotations -> Markdown skeleton), with
  round-trip golden tests.
- `sync/` package — prose write-back (`sync` verb) with `.lg2m.lock` baseline,
  3-way merge, surgical docstring and Markdown writers, `--prefer` conflict
  resolution, and `--dry-run`.

Success criteria met: `examples/support_pipeline` checks clean; a routing-drifted
copy returns non-zero with both locations; `check` writes nothing.

## Next (post-v0.1.0)

- **LangChain LCEL slice.** Emit the same Model-A mapping as a `RunnableBranch`;
  `gen --framework langchain`. Full fidelity stays LangGraph-only; LangChain
  covers linear chains + `RunnableBranch`.
- **CI version matrix.** Run the `@pytest.mark.langgraph` suite across a
  supported range of LangGraph / langchain-core versions so an upstream `Node` /
  `Edge` / `get_graph()` shape change surfaces as a test failure, not a user bug
  report.
- **Subgraph / `Send` / `Command` round-trip fidelity.** De-canonicalise
  flattened subgraph / `Send` / `Command` back into diagram sugar in both `gen`
  directions.
