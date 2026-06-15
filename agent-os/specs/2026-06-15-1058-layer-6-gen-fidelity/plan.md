## Execution Protocol (MANDATORY)

These rules govern any agent executing this plan. They are not optional.

1. **The checkbox is the source of truth.** A task is not complete until its checkbox in this file has been changed from `- [ ]` to `- [x]` using the Edit tool. Verbal claims of completion in chat are not completion.
2. **Flip immediately.** After finishing any action, edit this file to update the checkbox **before** beginning the next action. Do not batch checkbox updates across multiple tasks.
3. **Done-when gates are blocking.** If a task has a `### Done when` block, every item in it must be verifiably true before that task's checkbox may be flipped to `[x]`. No exceptions.
4. **Failure stops the run.** If any Done-when item cannot be satisfied, stop. Do not proceed to later tasks. Report the failure and wait for direction.
5. **No silent skips.** If a task is intentionally skipped, change `- [ ]` to `- [~]` and append a one-line note explaining why. Never delete a task.
6. **Self-audit before reporting completion.** Before telling the user the plan is done, re-read this file and confirm every checkbox is `[x]` or `[~]`. If any `[ ]` remains, the plan is not complete.

Violating these rules is a defect. Treat them as you would treat a failing test.

---

## Complexity

**Rating:** 5 — Very Complex

**Evidence:**
- Inverts the Layer 2 forward transform `canonicalize` (`src/lg2m/diff/assemble.py`, Rules A/B/C). A new `decanonicalize` must rebuild `<<fork>>`/`<<join>>`, single-level composites, and `[*]` from flat topology — new logic, not a tweak.
- Confirmed unknown resolved by exploration: `src/lg2m/introspect/langgraph_adapter.py::_edge` does **not** set `Edge.parallel`. `--from-code` must **infer** fork/join structurally (re-converging unconditional fan-out), which is a design task with its own correctness risk.
- Genuinely lossy edges (Send width is a runtime value; `Command(goto)` is only visible via declared `destinations`; >1-level composite nesting hits an upstream xray bug) must be scoped and documented, not faked.
- Cross-cutting: touches `diff/` (new inverse), `parsing/mermaid.py` (composite/pseudostate emission already present — verify it feeds the inverse), `scaffold/markdown.py`, `scaffold/generate.py`, and the round-trip goldens; Workstream B adds LCEL emission and the `router.as_runnable_branch()` vs scaffold-text decision.
- Acceptance bar promotes the lenient `support_pipeline` smoke to a **strict structural round-trip in both directions** — a measurable, all-or-nothing target across the whole example.

**Model Recommendation:** Opus.

**Reason:** Two new transforms (a lossy inverse and an LCEL emitter) with real correctness risk and a strict bidirectional round-trip target exceed what a lighter model should drive unaided.

**Context Warning (Rating 5):** A single session may exhaust context if both workstreams run end to end. **Split point: the Phase 1 → Phase 2 boundary.** Phase 1 (de-canonicalisation) is independently shippable — it retires the documented v1 limitation and strengthens the goldens on its own. Start Phase 2 (LangChain) in a fresh session if needed.

---

## Task 1: Save Spec Documentation

- [ ] Create `agent-os/specs/2026-06-15-1058-layer-6-gen-fidelity/` with plan.md, shape.md, standards.md, references.md, visuals/.

---

- [ ] **Phase 1: De-canonicalisation (Workstream A) — both directions**

  > Acceptance criteria for this phase: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 in `shape.md`.
  > This phase is the documented split point: it is shippable on its own.

  - [ ] **Task 1.1: Verify scope assumptions, then build the `decanonicalize` core**
    - [ ] Confirm against the running framework that the introspected code IR does **not** carry `Edge.parallel`, and that a flattened `parent:child` id breaks the mermaid round-trip (the `:` label-separator collision). Record the verified findings as a comment in the new module.
    - [ ] Add `decanonicalize(model: GraphModel) -> tuple[MermaidDiagram, dict[tuple[str, str], str]]` (diagram + edge-kind map), as the inverse of `canonicalize`. Place it next to its forward twin (`src/lg2m/diff/assemble.py`) or a sibling `src/lg2m/diff/decanonicalize.py`; keep it framework-free.
    - [ ] Inverse Rule C: edges to/from `__start__`/`__end__` (`START_ID`/`END_ID`) become `[*]` (`START_END`).
    - [ ] Inverse Rule A (fork/join): infer parallel fan-out/fan-in **structurally** (a source with ≥2 unconditional out-edges whose targets re-converge at a single node), since `Edge.parallel` is unset on the code side. Emit `MermaidState(pseudostate="fork")` / `("join")` and route the spliced edges through them.
    - [ ] Inverse Rule B (composite): group `parent:child` node ids by `parent`, reconstruct `state parent { [*] --> entry ... exit --> [*] }` with interior `MermaidEdge.scope = parent`, and rewire the parent's external in/out edges to the composite. **Single-level nesting only**; honour the depth limit and emit a diagnostic if exceeded.

  - [ ] **Task 1.2: Emit canonical-with-sugar markdown from `--from-code`**
    - [ ] Rewire `src/lg2m/scaffold/markdown.py::generate_markdown` (and its `_graph`) to feed `decanonicalize` output through the existing `emit_mermaid` (which already renders `pseudostate` and composite `state X { ... }` via `MermaidState`/`MermaidEdge.scope`).
    - [ ] Emit `Send`/`Command` as Edges-table `kind` values (`send`/`command`) plus the hidden `<!-- lg2m: ... -->` fences (`command_goto=`, `send_worker=...; width=dynamic`) and a `> Note:` for the dynamic Send width. Reuse `parsing/tables.py::emit_table`.
    - [ ] Remove or update the module docstring's "subgraph-free graphs round-trip exactly" limitation now that composites round-trip.

  - [ ] **Task 1.3: Regenerate the sugar as real code from `--from-doc`**
    - [ ] In `src/lg2m/scaffold/generate.py::_emit_graph`, reconstruct a nested `build_<parent>_subgraph()` and `add_node("<parent>", build_<parent>_subgraph())` when a node's doc flag `is_subgraph` is set (driven by the contract, not by flattened ids).
    - [ ] Emit a `Send` `fan_out_<x>` function + `add_conditional_edges(src, fan_out_<x>, ["<worker>"])` from the `send_worker` meta fence + Edges-table `kind=send`.
    - [ ] Emit a `Command` node body returning `Command(goto=...)` + `add_node(..., destinations=(...))` from the `command_goto` meta fence + Edges-table `kind=command`. Replace the v1 `# TODO: ... Send/Command is not generated by v1` markers.
    - [ ] Mirror `examples/support_pipeline/src/support_pipeline/{graph,nodes,routing}.py` exactly (builder shape, `destinations=`, `add_conditional_edges` arg order). Keep `scaffold/` framework-free.

  - [ ] **Task 1.4: Promote the goldens to strict round-trips**
    - [ ] Replace the lenient `support_pipeline` smokes (`test_scaffold_codegen.py::test_generate_code_on_full_example_parses`, `test_scaffold_markdown.py::test_example_smoke_is_well_sectioned`) with strict structural round-trips in **both** directions using `tests/_roundtrip.py::structural_key` identity equality.
    - [ ] Keep `tests/fixtures/mini_pipeline.md` as the fast framework-free unit-level round-trip check.

---

- [ ] **Phase 2: LangChain emission (Workstream B)**

  > Acceptance criteria for this phase: AC-8, AC-9 in `shape.md`. Begin in a fresh session if context is tight.

  - [ ] **Task 2.1: Source the RunnableBranch from the one router mapping**
    - [ ] Emit the `RunnableBranch` **text** in `scaffold/generate.py` directly from `model.routes[source].branches` (the same ordered mapping `_emit_routing` already reads), so LangGraph `path_fn` and LangChain `RunnableBranch` derive from one source and cannot drift — keeping `annotations/router.py` framework-free. (Alternative considered: add a lazy `router.as_runnable_branch()`; rejected to preserve the framework-isolation invariant on the router module. Revisit only if a test needs the live object.)
    - [ ] Key arms by **predicate name → target** in predicate order with `[else]` as the final default arm. Do **not** copy `examples/support_pipeline_native/langchain_app.py`'s target-keyed branch semantics.

  - [ ] **Task 2.2: Make `generate_code(model, framework="langchain")` emit LCEL**
    - [ ] Replace the `ScaffoldError` raise at `generate.py` with an LCEL emitter: chain edges via the `|` pipe / `RunnableSequence`; parallel fan-out via `RunnableParallel` + a `RunnableLambda` hand-merge (no channel reducer); conditional routing via the Task 2.1 `RunnableBranch`.
    - [ ] Document, in the emitted module and the spec, what LCEL cannot mirror (typed channels/reducers, `Send`, `Command(goto)`, sub-StateGraph, START/END) — mirror the "CANNOT mirror" list in `langchain_app.py`.

  - [ ] **Task 2.3: Test the weaker LangChain bar**
    - [ ] Add a `@pytest.mark.langgraph`-or-`langchain` test that builds the emitted LCEL graph, asserts it is a `Runnable`, and (optionally) executes a sample input and asserts it routes to the expected arm. State the limitation: no introspect-equality golden because there is no LangChain introspector.
    - [ ] Keep the hermetic subprocess check that `import lg2m.scaffold` / `import lg2m.cli` pull in no framework.

---

- [ ] **Phase 3: Finalize (docs + green)**

  > Acceptance criteria for this phase: AC-10 in `shape.md`.

  - [ ] **Task 3.1: Update design-of-record and roadmap**
    - [ ] Update `docs/design.md` Section 12 to retire the `gen` subgraph/`Send`/`Command`/LangChain limitation (scope the residual lossy edges precisely: Send width, `Command(goto)` without declared destinations, >1-level nesting).
    - [ ] Update the README roadmap "Next" list and the `pyproject.toml` `TODO(layer-…)` note if present.

  - [ ] **Task 3.2: Full green + lint**
    - [ ] `./.venv/bin/python -m pytest -q` passes including `@langgraph`, with coverage ≥ 90% on the `lg2m` package.
    - [ ] `./.venv/bin/ruff check src tests` is clean.
    - [ ] Confirm `gen` still writes only where asked (`--out` refuse-overwrite; no `--out` → stdout) via `CliRunner` exit-code tests (0 clean / 1 drift-or-structural / 2 usage-or-config).
