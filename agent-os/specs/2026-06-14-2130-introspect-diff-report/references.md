# References — lg2m layer 2b

## Design of record

- `docs/design.md` Section 4 — the three sources lg2m reconciles and what it verifies.
- `docs/design.md` Section 5 — package layout (note: `diff/assemble.py` is an intentional addition; see
  `shape.md` decision 3).
- `docs/design.md` Section 8 — the diff categories implemented in `diff/categories.py` / `diff/engine.py`.
- `docs/design.md` Section 9 — the worked drift examples reproduced as engine tests (route rename →
  `ROUTE_TARGET_MISMATCH`; drop `[else]` → `MISSING_ELSE`).
- `docs/design.md` Section 12 — limitations honored here: prose is report-only; subgraphs reconciled under
  `xray`; single-entry/single-exit composite constraint.
- `docs/design.md` Section 13 — build order; 2b is the "diff/engine + report against a Fake introspector".

## The oracle (read-only, the ground truth all three sources agree on)

- `examples/support_pipeline/docs/support_pipeline.md` — the Markdown contract: the
  `stateDiagram-v2` block, the `## Data Models` tables, the `## Edges` table (the `kind` column is
  the edge-classification authority), the `<!-- lg2m: ... -->` fences, and the `> Note:` block.
- `examples/support_pipeline/src/support_pipeline/state.py` — `@state_model PipelineState`
  (8 channels, 3 reducer kinds), `@data_model Ticket`, the custom `extend_unique` reducer.
- `examples/support_pipeline/src/support_pipeline/routing.py` — the `lg2m.router("classify_intent", …)`
  mapping (line 33) and the `Send` fan-out.
- `examples/support_pipeline/src/support_pipeline/predicates.py` — the two `@predicate`s.
- `examples/support_pipeline/src/support_pipeline/nodes.py` — the 12 `@node`s.
- `examples/support_pipeline/src/support_pipeline/graph.py` — the native `build_graph()`; the
  topology of record the `oracle_topology()` Fake reproduces in canonical form. **Imports langgraph;
  never imported by lg2m or its tests.**
- `examples/support_pipeline/lg2m.toml` — entry point + markdown path + `xray = true`.

## Seed reused

- `tests/test_round_trip_support_pipeline.py::build_graph_model` — the markdown→GraphModel assembly
  prototype extended into `src/lg2m/diff/assemble.py`.

## Implementation plan

- `~/.claude/plans/continue-lg2m-layer-2b-idempotent-cake.md` — the approved plan with the full
  canonicalization rules and the per-category check table.
