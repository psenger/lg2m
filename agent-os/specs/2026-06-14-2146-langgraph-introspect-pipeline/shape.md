# LangGraph introspector + runnable `check` pipeline — lg2m layer 3 (shape)

**Spec folder:** `agent-os/specs/2026-06-14-2146-langgraph-introspect-pipeline/`

## Scope

Layer 3 makes `lg2m check` run against the **real compiled LangGraph graph** for the first time. The
layer-2b reconciliation core works against a hand-authored Fake topology; this layer builds the
framework-importing adapter and the load/discovery pipeline so that, given
`examples/support_pipeline/lg2m.toml`, lg2m imports the user's factory, compiles it, reads the real
topology via `compiled.get_graph(xray=True)` + the state schema, and reconciles it against
`docs/support_pipeline.md` end-to-end.

**In scope:** `discovery/resolve.py`, `introspect/{schema,loader,langgraph_adapter}.py`, a
`pipeline.py` `check()` orchestrator, the layer-2b integration fix (Command-edge conditionality), and
`@pytest.mark.langgraph` tests against the real graph.

**Out of scope (a later spec):** the Typer `cli.py` (`init/list/validate/check/gen` + exit codes
0/1/2) and `scaffold/` (`gen --from-doc | --from-code`).

## Decisions

1. **The framework-isolation invariant holds.** Only `introspect/langgraph_adapter.py` imports
   `langgraph`/`langchain_core`, and `pipeline.check()` **lazy-imports** it, so `import lg2m`,
   `import lg2m.introspect`, and `import lg2m.pipeline` pull in no framework. `loader.py` runs user
   code (which imports the framework) but does not import it itself.
2. **The adapter returns the same `ir.GraphModel(origin="code")` the Fake authors.** `get_graph(
   xray=True)` already yields canonical vocabulary (flattened `parent:child` subgraph nodes,
   `__start__`/`__end__`, plain parallel edges), so no canonicalization runs on the code side —
   confirmed against `examples/support_pipeline_native/introspect.py`'s output.
3. **A framework-free `schema.py`** turns a state-schema / payload class into a `DataModel`
   (TypedDict via `get_type_hints(include_extras=True)` + `Annotated.__metadata__` reducers; pydantic
   `BaseModel` via duck-typed `model_fields`). Reducer names are normalized to reproduce the doc's
   hand-written strings: `operator.add` (module-qualified), `add_messages` / `extend_unique`
   (`__name__`). Name-level only (docs/design.md Section 12).
4. **The adapter also emits the `@data_model` payload models** (e.g. `Ticket`) by introspecting the
   live classes from the registry, so `assemble_code_model` stays unchanged.
5. **Install langgraph in the dev venv** and gate framework tests with `@pytest.mark.langgraph`; the
   suite still passes with `-m "not langgraph"`. The framework-free invariant becomes a **hermetic
   subprocess** test, because a marked test that imports the example leaves `langgraph` in
   `sys.modules`.
6. **Integration correction:** real `get_graph` reports the Command edge `escalate_to_human →
   compose_reply` as `conditional=True`; layer 2b marked it unconditional. Fix: add `"command"` to
   `diff/assemble.py`'s `_CONDITIONAL_KINDS` (doc side) and set the Fake's escalate edge conditional.

## Real `get_graph(xray=True)` findings (reference: native `introspect.py` + its README)

- Nodes: the canonical 14 (incl. `__start__`/`__end__`, `investigate:gather_logs`/`:analyze`).
- Edges: the canonical 16, each with `.source`/`.target`/`.conditional`/`.data`.
- **To verify against installed langgraph (Phase 3):** for a Model-A graph the conditional-edge
  `.data` is the `path_map` key = **predicate name** (docs/design.md Sections 3/4). The native example uses
  *target-named* keys, so it does not demonstrate this; only the lg2m-annotated graph does.
- **To verify (Phase 3):** the attribute exposing the state schema on a *compiled* graph
  (`builder.state_schema` vs `.schema`) is version-dependent.

## Quality gates

**Per-task Definition of Done.** Every task in `plan.md` ends with a `### Done when` checklist of
concrete commands/checks (tests pass, ruff clean, the real graph reconciles clean, the hermetic
invariant holds). No separate acceptance-criteria section.

## Context

- **Visuals:** none.
- **References:** see `references.md` — the native example, `config/loader.py`, the layer-2b
  assembler/engine, docs/design.md Sections 2/4/5/11/12.
- **Product alignment:** PLAN build order — this is layer 3 (the real introspector); the Typer CLI is
  the next layer.
