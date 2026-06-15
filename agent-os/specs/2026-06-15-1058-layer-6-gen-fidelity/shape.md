# Layer 6 — `gen` fidelity (de-canonicalisation + LangChain emission) — Shaping Notes

## Scope

Layer 6 of `lg2m`: make `gen` round-trip the **full** `support_pipeline` example in both
directions (not just the minimal subgraph-free fixture), and add LangChain as a `--from-doc`
target. Two workstreams, one combined phased spec with a split point at the phase boundary.

- **In (Phase 1, Workstream A — de-canonicalisation):** the inverse of the Layer 2 `canonicalize`
  pass. `--from-code` emits canonical-with-sugar mermaid (composites from `parent:child` ids,
  `<<fork>>`/`<<join>>` from parallel fan-out/fan-in, `[*]` sentinels, `Send`/`Command` via Edges
  `kind` + hidden fences + a `> Note:`). `--from-doc` regenerates that sugar as real code (nested
  `build_<parent>_subgraph()`, `Send` `fan_out_*`, `Command` node with `destinations=`). The full
  example then round-trips strictly; the minimal-fixture limitation is retired.
- **In (Phase 2, Workstream B — LangChain):** `generate_code(model, framework="langchain")` emits an
  LCEL graph (`RunnableSequence` / `RunnableParallel` + `RunnableLambda` hand-merge / `RunnableBranch`)
  instead of raising `ScaffoldError`.
- **In (Phase 3):** retire the documented limitation in `docs/design.md` Section 12 and the README
  roadmap; full green + ruff.
- **Out:** >1-level composite nesting (upstream xray bug; depth-limited); a LangChain introspector
  (none exists — hence the weaker LangChain test bar); prose `sync` / `.lg2m.lock` (`docs/prose-sync.md`,
  still out of scope); static reconstruction of Send fan width or `Command(goto)` without declared
  destinations (these stay metadata-driven and are documented as lossy).

## Decisions

1. **Combined phased spec, split at the A→B boundary.** Phase 1 is independently shippable; Phase 2
   may start in a fresh session (Rating 5 context-exhaustion risk).
2. **Infer fork/join structurally on the code side.** `LangGraphIntrospector._edge` does not set
   `Edge.parallel` (verified by exploration), so `--from-code` detects parallel as ≥2 unconditional
   out-edges that re-converge at a single join node, rather than reading a flag.
3. **`decanonicalize` is framework-free** and lives beside its forward twin in `diff/`. It returns a
   `MermaidDiagram` (+ edge-kind map) that feeds the existing `emit_mermaid`, which already renders
   pseudostates and composites via `MermaidState`/`MermaidEdge.scope`.
4. **`--from-doc` sugar is driven by the contract, not by flattened ids** — the doc's `is_subgraph`
   flag, the `command_goto` / `send_worker` meta fences, and the Edges-table `kind` column.
5. **LangChain RunnableBranch is emitted as text in `scaffold/` from the one `Route.branches` mapping**,
   not via a new `router.as_runnable_branch()`. Both the LangGraph `path_fn` and the LangChain branch
   derive from the same ordered mapping, so they cannot drift, and `annotations/router.py` stays
   framework-free (the load-bearing invariant). The `as_runnable_branch()` hook remains deferred.
6. **Branch keyed by predicate name, not target.** `examples/support_pipeline_native/langchain_app.py`
   keys its `RunnableBranch` arms on target functions; lg2m must not copy that — `path_map` is keyed by
   predicate name and `[else]` is the final default arm.
7. **Weaker, explicit LangChain bar.** No LangChain introspector exists, so the test builds the emitted
   LCEL, asserts it is a `Runnable`, and optionally asserts routing — not an introspect-equality golden.
8. **Lossy edges scoped and documented**, exactly as Layer 5 documented its limits: Send width is a
   runtime value, `Command(goto)` needs declared `destinations`, nesting is single-level.

## Round-trip semantics (the acceptance bar)

Strict equality is asserted on IR **identity** fields via `tests/_roundtrip.py::structural_key`
(`Node.id`/kind, `Edge(src_id, dst_id, predicate)`, `Route.branches`/`else_target`, `Predicate.name`,
`DataModel` name + attributes). Carried fields (prose, loc, meta, docstring) are ignored.

- **(a) code → markdown → IR:** introspect the full example → `generate_markdown` → `parse_markdown` +
  `assemble_doc_model` → equals the introspected code IR.
- **(b) markdown → code → introspect → IR:** `generate_code` on the full contract → write temp package →
  compile + introspect → equals `assemble_doc_model` of the same contract.

## Context

- **Visuals:** None.
- **References:** Layer 5 spec `agent-os/specs/2026-06-14-2301-scaffold-gen/`; Layer 4 spec
  `agent-os/specs/2026-06-14-2225-cli-typer/`; the working example `examples/support_pipeline/` and its
  contract `docs/support_pipeline.md`; the LCEL reference `examples/support_pipeline_native/langchain_app.py`.
  See `references.md`.
- **Product alignment:** `docs/design.md` Sections 3 (router compiles to both frameworks), 5 (layout),
  10 (scaffolding), 12 (limitations being retired), 13 item 5, 14 (golden round-trips).
- **Complexity:** Rating 5 (Very Complex); model Opus; split point at Phase 1 → Phase 2.
- **Quality gates:** Acceptance criteria up front (this file). `plan.md` carries no `### Done when`
  blocks; the executor verifies each phase against the AC IDs below.

## Acceptance Criteria

### AC-1: Full example code → markdown → IR round-trips strictly
**Given** the introspected `support_pipeline` code `GraphModel`
**When** it passes through `generate_markdown` → `parse_markdown` → `assemble_doc_model`
**Then** the result equals the original under `structural_key` identity equality.

### AC-2: Full example markdown → code → introspect → IR round-trips strictly
**Given** the `support_pipeline` Markdown contract
**When** `generate_code` emits the package, it is compiled and introspected, and reassembled
**Then** the result equals `assemble_doc_model` of the same contract under `structural_key`.

### AC-3: Composites are reconstructed from `parent:child` ids
**Given** a canonical `GraphModel` containing `investigate:gather_logs` / `investigate:analyze`
**When** `decanonicalize` runs
**Then** it emits a single-level `state investigate { [*] --> gather_logs ... analyze --> [*] }`
composite with the parent's external edges rewired, and the flattened `:` ids no longer leak into
top-level transitions.

### AC-4: Fork/join are reconstructed from parallel structure
**Given** a source node with ≥2 unconditional out-edges that re-converge at one join node (no
`Edge.parallel` flag present)
**When** `decanonicalize` runs
**Then** it emits `<<fork>>` and `<<join>>` pseudostates and routes the spliced edges through them.

### AC-5: `--from-code` expresses Send/Command without faking them
**Given** the example's `Send` fan-out and `Command(goto)` edges
**When** `generate_markdown` runs
**Then** they appear as Edges-table `kind=send` / `kind=command`, with `<!-- lg2m: send_worker=...; width=dynamic -->`
and `<!-- lg2m: command_goto=... -->` fences and a `> Note:` for the dynamic Send width.

### AC-6: `--from-doc` regenerates the sugar as real code
**Given** a contract with `is_subgraph`, a `send_worker` fence, and a `command_goto` fence
**When** `generate_code` runs
**Then** it emits a `build_<parent>_subgraph()` + `add_node("<parent>", build_<parent>_subgraph())`, a
`fan_out_*` + `add_conditional_edges(src, fan_out, ["<worker>"])`, and a `Command(goto=...)` node +
`add_node(..., destinations=(...))`, mirroring `examples/support_pipeline/src/support_pipeline/`, with
no `# TODO: ... not generated by v1` markers remaining.

### AC-7: The minimal fixture still passes as a fast unit check
**Given** `tests/fixtures/mini_pipeline.md`
**When** the framework-free subset runs (`-m "not langgraph"`)
**Then** its round-trip check still passes and remains fast.

### AC-8: LangChain emission builds and routes
**Given** a contract whose router has predicate arms ending in `[else]`
**When** `generate_code(model, framework="langchain")` runs and the emitted LCEL is built
**Then** building raises no error, the result is a `Runnable`, and (optionally) a sample input routes to
the predicate-ordered arm — keyed by predicate name, `[else]` last. No `ScaffoldError` is raised.

### AC-9: The emitter packages stay framework-free
**Given** a hermetic subprocess
**When** it runs `import lg2m.scaffold` and `import lg2m.cli`
**Then** no `langgraph` / `langchain_core` module is imported.

### AC-10: `gen` safety, exit codes, lint, and coverage hold
**Given** the full suite and CLI
**When** `pytest -q` (incl. `@langgraph`), `ruff check src tests`, and `CliRunner` gen tests run
**Then** the suite is green with ≥90% coverage, ruff is clean, `gen` writes only where asked
(`--out` refuses overwrite; no `--out` → stdout), and exit codes are 0 / 1 / 2 as specified.
