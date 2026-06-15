# Foundation Layer (IR + Config + Markdown/Mermaid Parsing) — Shaping Notes

## Scope

Build-order layer 1 of the `lg2m` Phase 1 MVP (`lg2m check` for LangGraph): the
**framework-free foundation**. In scope: `pyproject.toml`, `src/lg2m/__init__.py`
(export-surface stub), `src/lg2m/ir.py`, `src/lg2m/config/loader.py`, and
`src/lg2m/parsing/{markdown,tables,meta,mermaid}.py`, with tests. No
`langgraph` / `langchain_core` import anywhere in this layer.

Out of scope (later layers): annotations/decorators/router runtime,
`introspect/*` (the real framework adapter), `diff/*`, `report/*`, `cli.py`,
`scaffold/*`.

## Decisions

- **Scope cut at the framework boundary** so the layer is fully testable against
  the existing golden fixture without importing LangGraph. (`/shape-spec` scope
  question: "Foundation only".)
- **Packaging:** hatchling, PEP 621, `src/` layout, `requires-python >= 3.10`,
  PyPI, MIT. (`/plan-product` decision.)
- **TOML on 3.10:** stdlib `tomllib` is 3.11+, so a conditional `tomli`
  dependency for `python_version < "3.11"` plus an import shim. This is the one
  runtime dependency in the layer; it is conditional and canonical, and does not
  violate "own the parser" (which is about markdown/mermaid, not TOML).
- **No third-party markdown/mermaid/table libraries.** All four parsers are
  hand-rolled line scanners (docs/design.md Section 1: lg2m must own the parser).
- **IR identity enforced structurally** via frozen dataclasses with
  `field(compare=False)` on every non-identity field; `GraphModel` is the only
  mutable, non-frozen container (it is the parse-then-assemble buffer, never a
  dict key). See `plan.md` Appendix A for the reference implementation.
- **`[else]` is stored as `predicate="[else]"`, `is_else=True`** so the default
  branch keeps a distinct edge identity and round-trips its label verbatim; it is
  excluded from the `predicates` dict and from `Route.branches` (it is the
  `else_target`).
- **`GraphModel.meta` is a flat list** (not keyed by owner) because `map_items`
  owns both a hidden FENCE and a `> Note:`.
- **`__init__.py` is a stub** exporting only the IR names this layer needs, with
  a `# TODO(layer-2)` for the deferred public API (`node`, `predicate`, `router`,
  `ELSE`, `state_model`, `data_model`) that lands with the annotations layer.
- **Complexity: Rating 4 — Complex**, phased (4 phases), Opus; Phase 3 (Mermaid)
  is the context split point.
- **Quality gates: Done-when + Acceptance criteria.** Each task's `### Done when`
  in `plan.md` names the AC ids below.

## Context

- **Visuals:** None (CLI + library).
- **References:** `examples/support_pipeline/` (annotated golden fixture — the
  oracle) and `examples/support_pipeline_native/` (runnable LangGraph + LangChain
  baseline). See `references.md`.
- **Product alignment:** This spec *is* roadmap Phase 1, layer 1
  (`agent-os/product/roadmap.md`). Design of record: `docs/design.md` Sections 5, 6, 7.

## Standards Applied

Full text in `standards.md`. Why each applies:

- `global/value-objects` — the IR is value objects with explicit identity rules.
- `global/simplicity`, `global/clean-code` — minimal, no speculative abstraction
  (no builder, no grammar engine, no AST library).
- `global/coding-conventions` — Python naming/conventions for a public MIT package.
- `testing/testing`, `testing/mocking` — pytest layout + golden fixtures (no
  mocking needed in this framework-free layer).
- `global/hexagonal-architecture`, `patterns/adapter`, `global/coupling-cohesion`
  — forward constraint: keep this layer import-free of frameworks so the later
  introspection adapter is the only seam.
- `patterns/decorator` — informs the deferred `__init__` export surface.

## Acceptance Criteria

Stable ids; the `### Done when` blocks in `plan.md` reference them. All
counts/shapes are read from the real fixture
(`examples/support_pipeline/docs/support_pipeline.md`,
`examples/support_pipeline/lg2m.toml`).

### AC-01: config from pyproject
**Given** a `pyproject.toml` with `[tool.lg2m.graphs.<id>]`
**When** `config.loader.load()` reads it
**Then** it returns `{<id>: {...}}` preserving `graph`, `markdown`, `sys_path`, `xray`.

### AC-02: config from standalone toml
**Given** `examples/support_pipeline/lg2m.toml`
**When** loaded
**Then** `support_pipeline` maps to `graph == "support_pipeline.graph:build_graph"`, `markdown == "docs/support_pipeline.md"`, `sys_path == ["src"]`, `xray is True`; a pyproject `[tool.lg2m]` and a standalone `lg2m.toml` with the same content produce identical mappings.

### AC-03: TOML 3.10 shim
**Given** Python 3.10 (no stdlib `tomllib`)
**When** the loader imports
**Then** it falls back to `tomli`; on 3.11+ it uses stdlib `tomllib` with no extra dependency; TOML files are opened in binary mode.

### AC-04: frontmatter
**Given** the fixture
**When** parsed
**Then** `GraphModel.graph_id == "support_pipeline"` from the `lg2m_graph` frontmatter key.

### AC-05: diagram states
**Given** the mermaid block
**When** parsed
**Then** the named states are exactly: `ingest_ticket, fork_enrich, join_enrich, fetch_history, lookup_account, classify_intent, escalate_to_human, auto_resolve, investigate, gather_logs, analyze, map_items, process_item, reduce_items, compose_reply` (15; `[*]` is not a node).

### AC-06: fork/join pseudostates
**Given** `state fork_enrich <<fork>>` / `state join_enrich <<join>>` declaration lines
**When** parsed
**Then** `fork_enrich` carries pseudostate `fork` and `join_enrich` carries `join`; neither is read as a transition.

### AC-07: conditional fan-out + else + route
**Given** the three `classify_intent --> ...` lines
**When** parsed
**Then** there are exactly 3 conditional edges (`should_escalate -> escalate_to_human`, `should_auto_resolve -> auto_resolve`, `[else] -> investigate` with `is_else == True`); and exactly one `Route(source_id="classify_intent", branches=(("should_escalate","escalate_to_human"),("should_auto_resolve","auto_resolve")), else_target="investigate")`.

### AC-08: composite/subgraph
**Given** `state investigate { ... }`
**When** parsed
**Then** `investigate.is_subgraph == True` and its 3 internal edges (`[*] -> gather_logs`, `gather_logs -> analyze`, `analyze -> [*]`) are captured in the `investigate` scope.

### AC-09: start/end by position
**Given** top-level `[*] --> ingest_ticket` and `compose_reply --> [*]`
**When** parsed
**Then** left `[*]` resolves to START and right `[*]` to END; composite-internal `[*]` resolve to `investigate`'s local start/end, never coalesced with the top-level ones.

### AC-10: Send/Command are plain diagram edges
**Given** `map_items --> process_item` and `escalate_to_human --> compose_reply`
**When** parsed
**Then** both are ordinary unconditional edges (`predicate is None`, `conditional == False`); their Send/Command nature exists only as metadata (AC-13), not diagram syntax.

### AC-11: data models + reducers
**Given** `## Data Models`
**When** parsed
**Then** `models` has `PipelineState` (8 attributes, `is_graph_state == True` — its prose carries `@state_model`) and `Ticket` (4 attributes, `is_graph_state == False`); reducer names resolve to `add_messages` on `messages`, `operator.add` on `attempts` and `enrichment`, `extend_unique` on `item_results`, and `None` on `ticket/flags/items/resolution` and all four `Ticket` attributes. (`DataModel.style` — TypedDict vs BaseModel — is a code-side fact set by the later introspection layer, not encoded in the markdown, so it is not asserted at this layer.)

### AC-12: escaped pipe in table cell
**Given** the `Ticket` rows whose descriptions contain `` `'low'` \| `'normal'` \| `'high'` `` and `` `'free'` \| `'pro'` \| `'enterprise'` ``
**When** `tables.py` parses them
**Then** each row has exactly 4 cells and the description cell contains literal `|`, not extra columns.

### AC-13: three metadata mechanisms
**Given** the `###` node blocks
**When** `meta.py` parses
**Then** it yields a TABLE meta on `ingest_ticket`; FENCE metas on `classify_intent`, `escalate_to_human`, `map_items`, `reduce_items`; and a NOTE meta on `map_items`; `map_items` owns **both** a FENCE and a NOTE (two `Meta` entries, same `owner_id`), so `GraphModel.meta` is a flat list; total = 6 meta items.

### AC-14: fence payload decode
**Given** `<!-- lg2m: channel=enrichment; reducer=operator.add; merges=fetch_history,lookup_account -->`
**When** parsed
**Then** it decodes to `{"channel":"enrichment","reducer":"operator.add","merges":"fetch_history,lookup_account"}`; and `merges=process_item (Send)` keeps the trailing `(Send)` in the value (split pairs on `;`, key/value on first `=` only).

### AC-15: mermaid structural round-trip
**Given** the mermaid block
**When** `parse(block)` then `emit` then `parse` again
**Then** the two models are structurally equal on: set of node ids, each node's `is_subgraph` + pseudostate, and the ordered edge list `(src_id, dst_id, predicate, is_else, conditional)`; byte-exact text equality is **not** required.

### AC-16: IR identity
**Given** `Edge("classify_intent","escalate_to_human","should_escalate")` vs `Edge("classify_intent","auto_resolve","should_auto_resolve")`
**When** compared
**Then** same-key edges are equal and hash-equal and two predicates to the same target are distinct edges; given two `Node("investigate", ...)` differing only in `meta`/`prose`, they are equal (identity by `id`); a frozen instance rejects attribute rebinding.

### AC-17: Index table
**Given** `## Index`
**When** parsed
**Then** it has 15 rows = 13 `node` ids + 2 `predicate` ids; the predicate ids are `{should_escalate, should_auto_resolve}`; `fork_enrich` / `join_enrich` are **absent** from the Index (diagram pseudostates, distinct from the Index node ids even though both surfaces total 15 names).

### AC-18: Edges table
**Given** `## Edges`
**When** parsed
**Then** 17 rows are read with columns `from/to/label/kind/notes`; blank `label` cells become `""` (not `None`); the label column distinguishes the 3 conditional rows (`should_escalate`, `should_auto_resolve`, `[else]`) from the 14 unlabelled rows.
