# lg2m Layer 5 — `scaffold/` + `gen --from-doc | --from-code`

## Context

`lg2m` treats a Mermaid `stateDiagram-v2` (in Markdown) as a checkable contract for a
LangGraph graph. Layers 1–4 are done and green (165 tests, ~97% cov, ruff clean): the IR
and parsers, the annotations + router spine, the diff/report engine, the real LangGraph
introspector with a runnable `check`, and a Typer CLI (`check | validate | list | init`).

The one piece docs/design.md Section 13 (build-order item 5) defers to this layer is **generation**:
turning the contract into code and the code into a contract. This layer adds a framework-free
`scaffold/` package and a `gen` CLI command with two directions:

- `gen --from-doc` — read the Markdown contract, emit an annotated Python package
  (`@state_model`/`@data_model` classes, `@node`/`@predicate` stubs, a `lg2m.router(...)`
  mapping, and a complete `build_graph()`). **Pure string codegen; imports no framework.**
- `gen --from-code` — introspect the real compiled graph (the same load chain `check` uses)
  and emit a Markdown skeleton (canonical mermaid + metadata + prose as `TODO`).

The outcome: a user can bootstrap either side of the contract from the other, and the two
golden round-trips in docs/design.md Section 14 prove generation is structurally faithful.

**Decisions confirmed with the user:** both directions ship in this layer; emission targets
**LangGraph only** for v1 (the introspector and both goldens are LangGraph-only, so a
LangChain `RunnableBranch` emitter would ship untested — `--framework langchain` is rejected
with a clear exit-2 "not yet supported" message, keeping the flag forward-compatible);
output uses `--out` + refuse-to-overwrite (mirroring `init`) with a **stdout dry-run** when
`--out` is omitted; quality gate is **per-task Definition of Done**.

**Adopted defaults (from the kickoff, no framework needed):** `--from-code` emits *canonical*
mermaid (flat topology vocabulary — `[*]` sentinels, flattened `parent:child` subgraph nodes,
plain conditional edges; no `<<fork>>`/`<<join>>`/composite sugar). The round-trip is therefore
**structural** (IR identity fields), not byte-exact — re-parsing the emitted mermaid yields the
same IR. This limitation is documented. Codegen uses plain string templates (per-file emitters),
never an AST library, and `scaffold/` imports no framework. `--model-style` defaults to
`typeddict`. Prose is emitted as `TODO`; prose write-back / `.lg2m.lock` 3-way sync stays out
of scope for v1 (docs/design.md Section 12).

---

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

**Rating:** 4 — Complex

**Evidence:**
- Net-new `scaffold/` package with a **multi-file code emitter** (`state.py`, `nodes.py`,
  `predicates.py`, `routing.py`, `graph.py`, `__init__.py`) — a new pattern in this codebase.
- A net-new **Markdown-document emitter** (frontmatter + `##` sections + `###` entities +
  mermaid block): no such emitter exists today (confirmed — only `emit_table` and `emit_mermaid`
  primitives exist).
- New `gen` CLI command spanning two directions, reusing the introspect chain (`resolve` →
  `load_compiled` → `LangGraphIntrospector` → `gather_annotations` → `assemble_code_model`).
- Two `@pytest.mark.langgraph` **golden round-trips** requiring a temp-package write +
  compile + introspect harness, asserting structural IR equality.
- The **framework-isolation invariant**: `import lg2m.scaffold` and `import lg2m.cli` must pull
  in no framework; only the lazy adapter (reached by `--from-code`) may.

**Model Recommendation:** Opus
**Reason:** Cross-cutting (codegen + CLI + introspection reuse + tests), a new emitter pattern, and two non-trivial golden harnesses warrant the stronger model.

---

## Scope refinement (decided during execution, 2026-06-14)

**Verified empirically:** a flattened subgraph node id (`investigate:gather_logs`) cannot
round-trip through canonical mermaid — the `:` is mermaid's transition-label separator, so
`__start__ --> investigate:gather_logs` re-parses as an edge to `investigate` labelled
`gather_logs`. The full `support_pipeline` example also carries a `Send` fan-out and a
`Command(goto)` that introspect as synthetic conditional edges. Reconstructing subgraphs /
Send / Command from the flattened model is its own layer.

**Resolution (user-approved):** the **strict** golden round-trips use a **new minimal,
subgraph-free fixture** (`examples/mini_pipeline/` or `tests/fixtures/`): START/END, plain +
parallel edges, one conditional fan-out with two predicates + `[else]`, a `TypedDict` state
model (with `operator.add` / `add_messages` reducers) and a `data_model`. The full example
gets a **lenient smoke** only (`--from-doc` output parses with `ast.parse`; `--from-code`
output is non-empty and well-sectioned). Subgraph / `Send` / `Command` regeneration is a
**documented v1 `gen` limitation** (README + spec), alongside the existing canonicalization
limits. This replaces "on the example markdown" in Tasks 1.2 and 2.2 below.

---

## Task 1: Save Spec Documentation

- [x] Create `agent-os/specs/2026-06-14-2301-scaffold-gen/` with `plan.md`, `shape.md`, `standards.md`, `references.md`, and a `visuals/` dir containing `.gitkeep`.
- [x] `plan.md` = this plan (Context through Verification). `shape.md` = the **Shaping notes** appendix below. `standards.md` = the **Standards** appendix below. `references.md` = the **References** appendix below. Mirror the prior layer's spec format (`agent-os/specs/2026-06-14-2225-cli-typer/`).

---

- [x] **Phase 1: `--from-doc` code generation (framework-free)**

  - [x] **Task 1.1: `scaffold/` package + per-file code emitters**
    - [x] Create `src/lg2m/scaffold/__init__.py` (framework-free; exports the generate API).
    - [x] Add `scaffold/generate.py` with `generate_code(model: GraphModel, *, framework: str = "langgraph", model_style: str = "typeddict") -> dict[str, str]` returning `{filename: source}` for `__init__.py`, `state.py`, `nodes.py`, `predicates.py`, `routing.py`, `graph.py`.
    - [x] `state.py` emitter: one class per `DataModel`; `@state_model` for `is_graph_state`, else `@data_model`. `typeddict` → `TypedDict`; `pydantic` → `BaseModel`. Reducer-bearing attrs wrapped `Annotated[type, <reducer>]`; needed imports emitted; custom reducers (e.g. `extend_unique`) → an importable stub function.
    - [x] `nodes.py` emitter: `@node("id")` `NotImplementedError` stubs for each real node (sentinels excluded).
    - [x] `predicates.py` emitter: `@predicate("name")` stub per predicate referenced by a `Route`.
    - [x] `routing.py` emitter: `route_<source> = lg2m.router("<source>", [..., (lg2m.ELSE, "<else>")])` per `Route`, branch order.
    - [x] `graph.py` emitter: `build_graph()` → `StateGraph`, `add_node` per node, `add_edge` per unconditional edge, `add_conditional_edges(source, route_fn, route_fn.path_map)` per route, `START`/`END` edges; mirrors the example.
    - [x] `__init__.py` emitter: `from .graph import build_graph` / `__all__ = ["build_graph"]`.
    - [x] `--framework langchain` raises `ScaffoldError` (CLI maps to exit 2); `# TODO(langchain)` seam noted in the module docstring.

    ### Done when
    - [x] `tests/test_scaffold_codegen.py -m "not langgraph"` green (11 unit tests: every file `ast.parse`s; router mapping recovered via the AST reader; reducer wrapping; style + option errors).
    - [x] `python -c "import sys, lg2m.scaffold; assert 'langgraph' not in sys.modules and 'langchain_core' not in sys.modules"` exits 0.
    - [x] `ruff check src tests` is clean.

  - [x] **Task 1.2: md → code → introspect → IR golden (`@pytest.mark.langgraph`)**
    - [x] Shared harness `tests/_roundtrip.py`: write the `{filename: source}` package to `tmp_path` (unique pkg name per call), import, `build_graph()`, introspect via `LangGraphIntrospector`, `gather_annotations` + `assemble_code_model` (the `pipeline.check` chain). `structural_key` = identity-only view.
    - [x] Golden on the **minimal subgraph-free fixture** (`tests/fixtures/mini_pipeline.md`; scope refinement above): `generate_code` → temp package → compile + introspect → `structural_key(code) == structural_key(doc)` (nodes+kind, edges, routes, predicates, state model, models). **Verified exact** — the introspector even round-trips the nested `Payload` data model.
    - [x] Golden only introspects (never executes) the generated graph; the missing-predicate-import caveat does not bite.

    ### Done when
    - [x] `tests/test_scaffold_codegen.py` (incl. `@langgraph`) green — 12 passed.
    - [x] `ruff check src tests` is clean.

- [x] **Phase 2: `--from-code` Markdown emission**

  - [x] **Task 2.1: `scaffold/markdown.py` document emitter**
    - [x] `generate_markdown(model: GraphModel) -> str` produces the round-tripping contract shape: frontmatter (`lg2m_graph`), `## Index`, `## Graph` (fenced canonical mermaid), `## Data Models` (`### <name>` + attribute `emit_table`, `@state_model`/`@data_model` marker so `is_graph_state` round-trips), `## Predicates` / `## Nodes` (`TODO` prose + `Node.meta` fences when present), `## Edges` (`emit_table`).
    - [x] Canonical mermaid built from the code `GraphModel` (`[*]` for START/END) via `emit_mermaid`. Flat vocabulary only — fork/join/composite **not** reconstructed; a `:` in a flattened id does not round-trip (documented in the module).
    - [x] Reuses `emit_table` for every GFM table and `emit_mermaid` for the diagram.

    ### Done when
    - [x] `tests/test_scaffold_markdown.py -m "not langgraph"` green (round-trip structural equality; sections present; prose `TODO`; `@state_model`/`@data_model` markers).
    - [x] `python -c "import sys, lg2m.scaffold.markdown; assert 'langgraph' not in sys.modules"` exits 0.
    - [x] `ruff check src tests` is clean.

  - [x] **Task 2.2: code → markdown → IR golden (`@pytest.mark.langgraph`)**
    - [x] Golden (minimal fixture): introspect the generated package → `assemble_code_model` → `generate_markdown` → `parse_markdown` + `assemble_doc_model` → `structural_key` equal. Plus a **lenient smoke** on the real `support_pipeline` (introspect `golden_compiled` → emit → assert well-sectioned + parses; subgraph `:` ids do not round-trip).
    - [x] Reuses the `_roundtrip` harness for the introspect half.

    ### Done when
    - [x] `tests/test_scaffold_markdown.py` (incl. `@langgraph`) green — 6 passed.
    - [x] `ruff check src tests` is clean.

- [x] **Phase 3: `gen` CLI command + end-to-end**

  - [x] **Task 3.1: add the `gen` command to `src/lg2m/cli.py` (thin shell)**
    - [x] `@app.command()` `gen(...)` with module-level option constants: `--from-doc`/`--from-code` (exactly one, else exit 2), `--framework` (default `langgraph`; `langchain` → exit 2 via `ScaffoldError`), `--model-style` (default `typeddict`), `--out`, `graph_id`, `--config`. Reuses `_resolve_config` / `_load_graphs` / `_resolve_graph_id` / `_fail`.
    - [x] `--from-doc`: resolve config → `markdown_path` → `parse_markdown` + `assemble_doc_model` → `generate_code(...)`. `--out <dir>` writes the package (refuse-overwrite, checked before any write); no `--out` → stdout dry-run with per-file banners. Writes nothing on error.
    - [x] `--from-code`: new `pipeline.build_code_model(config, gid)` runs the `check` chain and returns the code `GraphModel` (or `None` + diagnostics on load failure) — the lazy framework import lives there, keeping `cli` framework-free. `generate_markdown(...)` → `--out <file>` (refuse-overwrite) or stdout. Load failure → diagnostics + exit 1; `ConfigError` → exit 2.
    - [x] `import lg2m.cli` confirmed framework-free (hermetic subprocess check).

    ### Done when
    - [x] `tests/test_cli_gen.py` green — 9 tests: exit 0 (both directions, dry-run + `--out` write), exit 2 (no/both flags, `--framework langchain`, unknown `--model-style`, overwrite refusal), exit 1 (load failure). `gen` writes only where asked (dry-run leaves inputs untouched; refused overwrite leaves the file unchanged).
    - [x] `python -c "import sys, lg2m.cli; assert 'langgraph' not in sys.modules and 'langchain_core' not in sys.modules"` exits 0.
    - [x] Full suite green — **193 passed, 96.33% cov** (gate 90%); `ruff check src tests` clean. Real CLI smoke verified on `examples/support_pipeline` (both directions).

---

## Critical Files

**New:**
- `src/lg2m/scaffold/__init__.py` — framework-free public API.
- `src/lg2m/scaffold/generate.py` — `generate_code(model, *, framework, model_style)` + the per-file code emitters.
- `src/lg2m/scaffold/markdown.py` — `generate_markdown(model)` document emitter.
- `src/lg2m/scaffold/writer.py` *(optional)* — `--out` file writing with refuse-to-overwrite.
- `tests/test_scaffold_codegen.py`, `tests/test_scaffold_markdown.py`, `tests/test_cli_gen.py`, and a shared round-trip harness (`tests/_roundtrip.py` or conftest fixture).

**Edited:**
- `src/lg2m/cli.py` — add the `gen` command + its option constants (reuse existing helpers).

**Reused unchanged (do not modify):**
- `src/lg2m/parsing/markdown.py` (`parse_markdown`), `src/lg2m/diff/assemble.py`
  (`assemble_doc_model`, `assemble_code_model`), `src/lg2m/parsing/tables.py` (`emit_table`),
  `src/lg2m/parsing/mermaid.py` (`emit_mermaid`, `MermaidDiagram`/`MermaidState`/`MermaidEdge`),
  `src/lg2m/annotations/router.py` (`router`, `ELSE`), `src/lg2m/ir.py`,
  `src/lg2m/discovery/resolve.py`, `src/lg2m/introspect/{loader,langgraph_adapter}.py`,
  `src/lg2m/pipeline.py` (`gather_annotations`, the `check` chain).

---

## Verification

1. `source .venv/bin/activate`
2. Framework-free subset: `./.venv/bin/python -m pytest -q -m "not langgraph"` (codegen + markdown-emitter unit tests + CLI exit codes).
3. Full suite incl. goldens: `./.venv/bin/python -m pytest -q` (the two `@langgraph` round-trips; 90% cov gate on `lg2m`).
4. Lint: `./.venv/bin/ruff check src tests` (clean; do not lint `examples/`).
5. Isolation: `./.venv/bin/python -c "import sys, lg2m.scaffold, lg2m.cli; assert 'langgraph' not in sys.modules and 'langchain_core' not in sys.modules"`.
6. Smoke the CLI: `cd examples/support_pipeline && ../../.venv/bin/lg2m gen --from-doc` (stdout dry-run) and `... gen --from-code` (stdout markdown); confirm `--out` refuses to overwrite an existing path.

---


See `shape.md` for shaping decisions, `standards.md` for applicable standards, and
`references.md` for the exact wiring this layer reuses.
