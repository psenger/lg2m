# Introspect + Diff + Report — lg2m layer 2b (shape)

**Spec folder:** `agent-os/specs/2026-06-14-2130-introspect-diff-report/`

## Scope

Layer 2b is the **reconciliation core** of `lg2m check`, minus the CLI (layer 4) and
minus the real framework adapter (layer 3). It reduces the three sources lg2m verifies
(docs/design.md Section 4) to one `DriftReport`.

**In scope (new):**
- `introspect/{base,__init__}.py` — the `GraphIntrospector` Protocol + a framework-free
  `FakeIntrospector`.
- `diff/{categories,assemble,engine,__init__}.py` — drift vocabulary, the two-sided
  `GraphModel` assembler + the canonicalization pass, and `reconcile`.
- `report/{model,text,json,__init__}.py` — the `DriftReport` value model and its renderers.

**Out of scope (later layers):** `introspect/langgraph_adapter.py` (the only file that imports
the framework, layer 3), `cli.py` + the `check`/`gen` commands (layer 4), `scaffold/`.

**Invariant:** importing `lg2m` (and now `lg2m.introspect`, `lg2m.diff`, `lg2m.report`) pulls in
no framework. The annotation source for the oracle test is recovered with the AST reader (no
import), since the example modules import `langgraph`, which the dev venv does not install.

## Decisions

1. **Introspector returns `ir.GraphModel(origin="code")`** (docs/design.md Section 5: "topology IR"), not a
   new `Topology` type. Third-party-shape → domain translation lives inside each adapter
   (hexagonal-architecture.md), so the future `langgraph_adapter` is substitutable for the Fake.
2. **Canonical form = topology vocabulary.** The diagram's `<<fork>>`/`<<join>>` pseudostates and
   `investigate` composite have no analogue in `get_graph(xray=True)` (plain parallel edges,
   flattened `parent:child` nodes, `__start__`/`__end__`). The cheap, near-mechanical adapter side
   cannot reconstruct them, so the **diagram side absorbs the transformation** in `canonicalize`,
   which runs on the doc side only. The code side is already canonical and is only decorated with
   annotation facts.
3. **A dedicated `diff/assemble.py`.** Keeps `reconcile` a pure comparison of two assembled
   `GraphModel`s. **Deviation from docs/design.md Section 5**, which lists only `diff/engine.py` +
   `diff/categories.py`; `assemble.py` is added because the canonicalization pass is the single
   hardest, most load-bearing piece of 2b and does not belong inside the comparison core.
4. **`DriftCategory` (cross-source outcomes) stays distinct from `ir.DiagnosticKind`
   (single-source structural facts).** The engine **folds** each parse/introspect `Diagnostic` into
   a `DriftItem` via `DIAGNOSTIC_MAP`, so there is one report and one exit path.
5. **Edge-flag authority = the `## Edges` table `kind` column.** The mermaid block is the authority
   for connectivity; the table classifies each edge (`send` → conditional, `command`, `parallel`).
6. **`PROSE_DRIFT` is WARNING-only and fires only when both sides carry prose** (docs/design.md Section 12:
   v1 reports prose drift, never writes back). The Fake's absent docstrings keep the oracle clean.
7. **`canonicalize` handles single-entry/single-exit composites**; a multi-entry/exit composite
   emits a diagnostic rather than guessing (docs/design.md Section 12 already caps nesting depth).

## Canonical oracle sets (the contract both sides hit)

**Nodes (14):** `__start__`, `ingest_ticket`, `fetch_history`, `lookup_account`, `classify_intent`,
`auto_resolve`, `escalate_to_human`, `investigate:gather_logs`, `investigate:analyze`, `map_items`,
`process_item`, `reduce_items`, `compose_reply`, `__end__`. (No `fork_enrich`, `join_enrich`,
`investigate`.)

**Edges (16)** by identity `(src, dst, predicate)`: the START edge; two parallel fan-out edges from
`ingest_ticket`; two fan-in edges to `classify_intent`; the three conditional branches
(`should_escalate`, `should_auto_resolve`, `[else]` → `investigate:gather_logs`); the two interior
subgraph edges; the Send edge `map_items → process_item` (conditional); the linear
`process_item → reduce_items → compose_reply`; `auto_resolve → compose_reply`; the Command edge
`escalate_to_human → compose_reply`; and `compose_reply → __end__`.

## Acceptance Criteria

- **AC-clean.** Assembling all three sources from the real `examples/support_pipeline/` files and the
  `oracle_topology()` Fake, `reconcile(...)` returns `DriftReport(items=[])` with `exit_code == 0`.
- **AC-canonical.** `assemble_doc_model` on the real `support_pipeline.md` yields exactly the 14-node
  / 16-edge canonical sets; the fork/join pseudostates and the `investigate` composite are gone.
- **AC-code-side.** `assemble_code_model` decorates the topology so every real node carries an
  `anno_id` (the subgraph nodes via `<parent>:<id>` suffix match); routes/predicates/models come
  from the registry with real `file:line` from the reader.
- **AC-per-category.** One injected-drift test per Section 8 category produces exactly that
  `DriftCategory` at the right severity.
- **AC-section9.** Renaming a code-side route target yields `ROUTE_TARGET_MISMATCH` (both locs);
  dropping the diagram `[else]` yields `MISSING_ELSE`.
- **AC-fold.** Parse/introspect `Diagnostic`s fold into `DriftItem`s; `--strict` escalates WARNING
  diagnostics to ERROR.
- **AC-render.** A clean report renders "0 drift items"; a drifted report lists items with both
  locations; `render_json` round-trips through `json.loads`.
- **AC-framework-free.** Importing `lg2m` and the new packages leaves `langgraph` /
  `langchain_core` out of `sys.modules`.
- **AC-coverage.** Full suite green; the 90% coverage gate holds on `lg2m`; `ruff check src tests`
  clean.

## Context

- **Oracle (read-only):** `examples/support_pipeline/docs/support_pipeline.md`,
  `src/support_pipeline/{state,routing,predicates,nodes}.py`, `lg2m.toml`.
- **Seed:** `tests/test_round_trip_support_pipeline.py::build_graph_model` (extended into
  `diff/assemble.py`).
- **Design of record:** docs/design.md Sections 4, 5, 8, 9, 12, 13.
- **Visuals:** none.
