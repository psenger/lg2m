# lg2m Layer 3 — the real LangGraph introspector + runnable `check` pipeline

## Context

Layers 1 (IR + parsers), 2a (annotations + router), and 2b (introspect Fake + diff + report) are done
and green. The reconciliation core works against a hand-authored Fake topology. Layer 3 makes `check`
work against the **real compiled LangGraph graph**: lg2m imports the user's factory, compiles it, reads
the real topology via `compiled.get_graph(xray=True)` + the state schema, and reconciles it against the
Markdown contract. Scope, decisions, and the real-`get_graph` findings are in `shape.md`.

## Execution Protocol (MANDATORY)

These rules govern any agent executing this plan. They are not optional.

1. **The checkbox is the source of truth.** A task is not complete until its checkbox in this file has been changed from `- [ ]` to `- [x]` using the Edit tool. Verbal claims of completion in chat are not completion.
2. **Flip immediately.** After finishing any action, edit this file to update the checkbox **before** beginning the next action. Do not batch checkbox updates across multiple tasks.
3. **Done-when gates are blocking.** If a task has a `### Done when` block, every item in it must be verifiably true before that task's checkbox may be flipped to `[x]`. No exceptions.
4. **Failure stops the run.** If any Done-when item cannot be satisfied, stop. Do not proceed to later tasks. Report the failure and wait for direction.
5. **No silent skips.** If a task is intentionally skipped, change `- [ ]` to `- [~]` and append a one-line note explaining why. Never delete a task.
6. **Self-audit before reporting completion.** Before telling the user the plan is done, re-read this file and confirm every checkbox is `[x]` or `[~]`. If any `[ ]` remains, the plan is not complete.

Violating these rules is a defect. Treat them as you would treat a failing test.

## Complexity

**Rating:** 4 — Complex

**Evidence:**
- Cross-cutting pipeline: new `discovery/resolve.py`, `introspect/{schema,loader,langgraph_adapter}.py`,
  `pipeline.py`, wiring config → load → introspect → read → assemble → reconcile → report.
- First framework dependency in the dev venv; first `@pytest.mark.langgraph` tests; a test-isolation
  hazard (the framework-free invariant must become a hermetic subprocess check).
- Integration correction to shipped layer-2b code (`diff/assemble.py`, `tests/_oracle.py`).
- Untrusted-code boundary: import + run + compile user code; `IMPORT_FAILURE` diagnostics with location.
- Real unknowns verifiable only against installed langgraph: the Model-A label=predicate-name
  assumption; the compiled-graph state-schema attribute; reducer-string normalization.

**Model Recommendation:** Opus.
**Context note:** natural split after Phase 3 (adapter green against the real graph).

## Task 1: Save Spec Documentation

- [x] Create this spec folder with `plan.md`, `shape.md`, `standards.md`, `references.md`, `visuals/`.

### Done when
- [x] All five entries exist and the four markdown files are non-empty.
- [x] `shape.md` records the Command-edge fix and the label=predicate-name verification.

## Phase 1: Environment + hermetic framework-free test

- [x] **Task 1.1: install the langgraph extra** — installed langgraph 1.2.5 / langchain-core 1.4.7.
  ### Done when
  - [x] `import langgraph, langchain_core` works; full suite still green (122); `from support_pipeline.graph import build_graph` works with `examples/support_pipeline/src` on the path. (Also verified the real `get_graph(xray=True)`: 14 nodes / 16 edges, conditional-edge `.data` = predicate name, `builder.state_schema` exposes `PipelineState`.)
- [x] **Task 1.2: hermetic framework-free invariant** — replaced the in-process assert in `tests/test_introspect.py` with a `subprocess` check.
  ### Done when
  - [x] The subprocess test passes; ruff clean; passes even after a `@langgraph` test imported the framework earlier in the session.

## Phase 2: Framework-free schema introspection

- [x] **Task 2.1: `introspect/schema.py` — `model_from_class`** (TypedDict via `get_type_hints` + `Annotated.__metadata__`; pydantic via `model_fields`); `_reducer_name` normalizer (`operator.<n>` when module is `operator`, else `__name__`); no `import langgraph`.
  ### Done when
  - [x] A test on a local `TypedDict` + duck-typed pydantic stub asserts attributes/types/reducers/style; no framework import statement; ruff clean.

## Phase 3: The LangGraph adapter (only framework-importing module)

- [x] **Task 3.1: `introspect/langgraph_adapter.py` — `LangGraphIntrospector(compiled, *, xray=True)`** → canonical `GraphModel(origin="code")`: nodes (START/END/NODE), edges (`predicate` from `e.data` when conditional, `is_else`, `conditional`), state schema via `schema.py`, `@data_model` payload models from the registry. Framework-coupled but import-light (duck-typed); not imported by `introspect/__init__.py`. (Also fixed the `add_messages` reducer name via public-binding resolution, and made the layer-2a reader "no import" assertion hermetic.)
  ### Done when (all `@pytest.mark.langgraph`, real `build_graph()`)
  - [x] nodes == canonical 14; edges == canonical 16 (reuse `tests/test_assemble.py` constants).
  - [x] **Verified:** classify branches carry `.data` = predicate names; `[else]` edge `is_else=True` → `investigate:gather_logs`.
  - [x] **Verified:** `escalate_to_human → compose_reply` conditional; `map_items → process_item` conditional, `predicate=None`.
  - [x] `PipelineState` 8 attrs w/ reducers; `Ticket` 4 `str` attrs; `state_model_name == "PipelineState"`.
  - [x] `import lg2m.introspect` imports no langgraph (hermetic subprocess).

## Phase 4: Loader + discovery

- [x] **Task 4.1: `discovery/resolve.py`** — `resolve(cfg, *, base_dir, graph_id) -> ResolvedGraph` (split `mod:attr`, resolve paths, defaults; `ConfigError` on missing `graph`/`markdown`); `discovery/__init__.py`.
  ### Done when
  - [x] Test on the real `lg2m.toml` yields module/attr/abs paths/`xray`; malformed → `ConfigError`; framework-free; ruff clean.
- [x] **Task 4.2: `introspect/loader.py`** — `load_compiled(resolved) -> LoadedGraph`; prepend `sys_paths`, import module (populates registry), run factory; catch import/attr/exception → `IMPORT_FAILURE` diagnostic; no `import langgraph`.
  ### Done when
  - [x] `@langgraph`: real example → compiled graph + live registry (12 nodes / 2 models / 1 router). **Correction:** `@predicate`s are NOT live (predicates.py isn't in graph.py's import chain — the Model-A router resolves names lazily); the pipeline discovers them via the AST reader in Phase 5. Documented in `test_loader.py`.
  - [x] Framework-free: missing module → one `IMPORT_FAILURE` diagnostic, no exception escapes; ruff clean.

## Phase 5: Integration fix + `check()` orchestrator + end-to-end

- [x] **Task 5.1: layer-2b correction** — added `"command"` to `_CONDITIONAL_KINDS`; set `tests/_oracle.py` escalate edge conditional.
  ### Done when
  - [x] Layer-2b suite stays green (clean oracle still empty); ruff clean.
- [x] **Task 5.2: `pipeline.py`** — `gather_annotations(package_dir)` (AST reader over the package's source files + router locs, the complete annotation set) and `check(config_path, graph_id, *, strict=False) -> DriftReport` wiring config→resolve→load→(lazy) adapter→annotations→assemble→reconcile. (Reader-over-source replaces the incomplete live registry for annotations.)
  ### Done when
  - [x] Hermetic subprocess: `import lg2m.pipeline` imports no langgraph.
  - [x] `@langgraph` end-to-end: `check(examples/support_pipeline/lg2m.toml, "support_pipeline")` → `is_clean`, `exit_code == 0` (the milestone; also verified from a fresh interpreter).
  - [x] `@langgraph` drift: a markdown copy with a renamed node → `NODE_MISSING_IN_DOC`/`_IN_CODE`, exit 1. Plus a framework-free import-failure path test.
- [x] **Task 5.3: full-suite + invariants gate**
  ### Done when
  - [x] `pytest -q` all green incl. `@langgraph` (142); 90% coverage gate holds (~96%); `pytest -q -m "not langgraph"` green (134, 8 deselected); ruff clean; hermetic invariant passes.

## Critical Files

- New: `src/lg2m/discovery/{__init__,resolve}.py`, `src/lg2m/introspect/{schema,loader,langgraph_adapter}.py`,
  `src/lg2m/pipeline.py`, `tests/test_{schema,langgraph_adapter,loader,resolve,pipeline}.py`.
- Edited (small): `src/lg2m/diff/assemble.py` (`+"command"`), `tests/_oracle.py` (escalate edge),
  `tests/test_introspect.py` (hermetic invariant).
- Reused unchanged: `ir.py`, `annotations/{registry,reader}.py`, `parsing/*`, `diff/{engine,categories}.py`,
  `report/*`, `assemble_code_model`/`assemble_doc_model`.
- Read-only oracle: `examples/support_pipeline/`; `examples/support_pipeline_native/introspect.py`.

## Verification

```bash
source .venv/bin/activate
pip install -e '.[langgraph]'
python -m pytest -q                       # all green incl. @langgraph; 90% gate holds
python -m pytest -q -m "not langgraph"    # suite still runs framework-free
ruff check src tests
python -c "import sys, lg2m, lg2m.pipeline, lg2m.introspect; assert 'langgraph' not in sys.modules"
python -c "from pathlib import Path; from lg2m.pipeline import check; \
  r = check(Path('examples/support_pipeline/lg2m.toml'), 'support_pipeline'); print(r.exit_code, r.is_clean)"
```
