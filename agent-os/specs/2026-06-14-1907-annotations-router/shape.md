# Annotations + Router (lg2m layer 2a) — Shaping Notes

## Scope

Build-order layer 2a of the lg2m Phase 1 MVP: the **authoring annotations and the
Model-A router**. In scope: `src/lg2m/annotations/{__init__,registry,decorators,router,reader}.py`
and the `src/lg2m/__init__.py` export fill-in, plus small edits to `ir.py`
(hoist `ELSE_LABEL`) and `parsing/mermaid.py` (import it). No `langgraph` /
`langchain_core` import anywhere in lg2m code or its tests.

Out of scope (later slices): `introspect/*` (Fake or real), `diff/*`, `report/*`,
`cli.py`, `scaffold/*`, and the router's `.as_runnable_branch()` LangChain emit
(deferred to the LangChain layer; present only as a docstring hook).

## Decisions

- **Scope cut at the annotation surface** so the layer is fully testable against
  the example without the introspector or diff engine.
- **`ELSE_LABEL` has one home:** hoisted from `parsing/mermaid.py` to `ir.py`;
  `mermaid.py` and `annotations/*` import it. The router `path_map` default, the
  IR `Route` default, the predicate guard, and the reader's recovered ELSE all
  use that one literal `"[else]"`, which is why the label check can hold by
  construction.
- **Decorators are metadata-only:** `@node("id")`/`@predicate("name")` are
  parametrized; `@state_model`/`@data_model` are bare class decorators; all record
  into a per-import registry and return the target unchanged.
- **Lazy predicate resolution:** `routing.py` does not import `predicates.py`, so
  the generated `path_fn` resolves predicate names to `@predicate` functions from
  the registry at call time, returning the matched **name** (or `"[else]"`).
- **Missing predicate at call time raises `LookupError`** (the non-fatal static
  signal `PREDICATE_UNDEFINED` is the later diff layer's job).
- **Annotation location = the decorator line** (`decorator_list[i].lineno`),
  recovered by the AST reader, which is authoritative over the runtime best-effort
  line.
- **Reader stays single-responsibility:** pure `ast` recovery + a thin
  `merge_locations(result, registry)`; `GraphModel` assembly is the diff layer's.
- **Complexity: Rating 4 — Complex**, phased (decorators+registry / router /
  reader), Opus; Phase 3 (reader) is the context split point.
- **Quality gates: Done-when + Acceptance criteria.**

## Context

- **Visuals:** None.
- **References:** the example annotation files
  `examples/support_pipeline/src/support_pipeline/{routing,predicates,state,nodes}.py`
  (the oracle), and `docs/design.md` Sections 3 (routing model), 4 (what is verified),
  14 (test strategy). See `references.md`.
- **Product alignment:** roadmap Phase 1, build-order layer 2a; depends on the
  completed layer-1 foundation (the IR + parsers, 51 tests green).

## Standards Applied

Full text in `standards.md`. The annotations/router and testing bundles are
active here; the introspection-seam and diff/diagnostics bundles are forward
constraints (keep this layer framework-free; shape validation and the
`LookupError`/`ValueError` boundaries so the later diff layer's diagnostics slot
in). The layer-1 restraint set carries over.

## Acceptance Criteria

Stable ids; the `### Done when` blocks in `plan.md` reference them. All
counts/lines are read from the real example files under
`examples/support_pipeline/src/support_pipeline/`.

### AC-01: node decorator
**Given** `@node("ingest_ticket")` on a function
**When** the module imports
**Then** `registry.nodes["ingest_ticket"].target` is that function and the function is returned unchanged (still callable).

### AC-02: predicate decorator
**Given** `@predicate("should_escalate")` on a function
**When** imported
**Then** `registry.predicates["should_escalate"].target` is that function, returned unchanged.

### AC-03: data_model bare
**Given** `@data_model` on `class Ticket`
**When** imported
**Then** `registry.models["Ticket"]` exists with `is_graph_state is False`, class returned unchanged.

### AC-04: state_model bare
**Given** `@state_model` on `class PipelineState`
**When** imported
**Then** `registry.models["PipelineState"].is_graph_state is True`.

### AC-05: path_map
**Given** `lg2m.router("classify_intent", [("should_escalate","escalate_to_human"),("should_auto_resolve","auto_resolve"),(lg2m.ELSE,"investigate")])`
**Then** `router.path_map == {"should_escalate":"escalate_to_human","should_auto_resolve":"auto_resolve","[else]":"investigate"}` and `router.source`/`router.branches`/`router.else_target` match.

### AC-06: returns the name
**Given** that router and a registered `@predicate("should_escalate")` truthy for the test state
**When** the path_fn is called
**Then** it returns `"should_escalate"` (the name, not the target).

### AC-07: else
**Given** the same router
**When** every predicate is falsy
**Then** the path_fn returns `"[else]"`.

### AC-08: first-match order
**Given** `should_escalate` falsy and `should_auto_resolve` truthy
**Then** the path_fn returns `"should_auto_resolve"` (ordered scan; the else default is never scanned regardless of its position in the list).

### AC-09: missing else
**Given** branches with no `ELSE`
**Then** `lg2m.router(...)` raises `ValueError` about the missing default.

### AC-10: reserved label as a predicate key
**Given** a branch keyed by the string `"[else]"` (not the sentinel)
**Then** construction raises `ValueError` rejecting the reserved label.

### AC-11: duplicate else
**Given** two `ELSE` elements
**Then** construction raises `ValueError` ("more than one ELSE").

### AC-12: predicate named else
**Given** `@predicate("[else]")`
**Then** the decorator raises `ValueError`.

### AC-13: two predicates, one target
**Given** branches `("a","compose_reply")` and `("b","compose_reply")`
**Then** `path_map` has two distinct keys both mapping to `"compose_reply"` (two labelled edges).

### AC-14: undefined predicate at call
**Given** a router referencing `"should_escalate"` with no such `@predicate` registered
**When** the path_fn is called
**Then** it raises `LookupError` naming the source and the missing predicate.

### AC-15: reader recovers the route
**Given** the reader parses `routing.py` as text (no import)
**Then** it recovers `Route(source_id="classify_intent", branches=(("should_escalate","escalate_to_human"),("should_auto_resolve","auto_resolve")), else_target="investigate")` with `loc.file` = that path and `loc.line == 33`.

### AC-16: reader recovers predicates
**Given** the reader parses `predicates.py`
**Then** it recovers predicate `AnnoRef`s for `should_escalate` (decorator line 20) and `should_auto_resolve` (line 26).

### AC-17: reader recovers models
**Given** the reader parses `state.py`
**Then** it recovers `("data_model","Ticket", line 41)` and `("state_model","PipelineState", line 51)`, distinguishing the two bare decorators by kind.

### AC-18: reader recovers nodes
**Given** the reader parses `nodes.py`
**Then** it recovers exactly **12** node `AnnoRef`s with ids `{ingest_ticket, fetch_history, lookup_account, classify_intent, auto_resolve, escalate_to_human, map_items, process_item, reduce_items, compose_reply, gather_logs, analyze}` (representative decorator lines: `ingest_ticket`@23, `analyze`@130); `investigate` is **not** among them (subgraph, no `@node`); and parsing does **not** import `nodes.py` (so `langgraph` is not imported).

### AC-19: ELSE both spellings
**Given** a file using `from lg2m import ELSE` and a bare `ELSE` in the branches
**Then** the reader recovers the same `else_target` as the `lg2m.ELSE` attribute form.

### AC-20: public exports, no framework import
**Given** `import lg2m`
**Then** `lg2m.node`, `lg2m.predicate`, `lg2m.router`, `lg2m.ELSE`, `lg2m.state_model`, `lg2m.data_model` are all present, and `"langgraph" not in sys.modules` as a result of importing lg2m.
