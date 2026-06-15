# References for Annotations + Router (lg2m layer 2a)

## The oracle: the example annotation files

Location: `examples/support_pipeline/src/support_pipeline/`. These are the exact
authoring surface the decorators/router/reader must match. **Read-only** — the
implementation conforms to them.

### `routing.py`
- `import lg2m`; `route_after_classify = lg2m.router("classify_intent", [(...), (...), (lg2m.ELSE, "investigate")])` at **line 33**.
- Crucially does **not** import `predicates.py`, which is why the router must
  resolve predicate names from the registry **lazily** at call time.
- Also defines `fan_out_items` (native `Send` map-reduce) — out of scope here; the
  router never owns `Send`.

### `predicates.py`
- `from lg2m import predicate`; `@predicate("should_escalate")` (decorator **line 20**),
  `@predicate("should_auto_resolve")` (**line 26**). Bodies hold the `and`/`or`/`not`;
  lg2m never reads them.

### `state.py`
- `from lg2m import data_model, state_model`; `@data_model class Ticket` (**line 41**),
  `@state_model class PipelineState` (**line 51**). Bare decorators, distinguished
  by kind (`is_graph_state`).

### `nodes.py`
- `from lg2m import node`; **12** `@node("...")` decorators (lines 23, 39, 45, 53,
  67, 75, 94, 101, 108, 115, 124, 130). Note `investigate` is the compiled subgraph
  and carries **no** `@node`, so there are 12 annotated nodes vs 13 diagram/Index
  node ids — a gap the later diff layer reconciles, not this one.
- Imports `langgraph.types` — so the AST reader must parse it as **text**, never
  import it.

## Design of Record

- `docs/design.md` Section 3 — the routing model: Model A, generated; the path_fn returns
  the matched predicate name; lg2m owns the `path_map` keyed by predicate name;
  `[else]` required.
- `docs/design.md` Section 4 — what is verified: every routing predicate is a defined
  `@predicate`; the router mapping == `path_map` by construction; every fan-out has
  `[else]`.
- `docs/design.md` Section 14 — the test strategy bullets "Router generation" and
  "Annotation reader / AST".

## Reused from layer 1

- `src/lg2m/ir.py` — the value-object targets (`Route`, `SourceLocation`, `Node`,
  `Predicate`, `DataModel`) the registry and reader feed into. Gains `ELSE_LABEL`.
- `src/lg2m/parsing/mermaid.py` — currently owns `ELSE_LABEL = "[else]"`; will
  import it from `ir.py` after the hoist.
- `tests/conftest.py` — the existing `sys.path` + golden-fixture fixtures; gains the
  autouse `reset_registry` fixture.
- `.venv/` — the layer-1 toolchain (pytest + ruff) is already installed.
