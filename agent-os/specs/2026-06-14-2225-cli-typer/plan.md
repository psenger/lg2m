# lg2m Layer 4 — Typer CLI over the check pipeline

## Context

Layers 1–3 are done and green (142 tests, ~96% coverage, ruff clean). Reconciliation
works end-to-end **programmatically**: `lg2m.pipeline.check(config_path, graph_id, *, strict=False)`
returns a `DriftReport` against the real compiled LangGraph graph, and `report.render_text` /
`report.render_json` render it. What is missing is the **user-facing entry point**: there is no
`lg2m` command. docs/design.md Section 11 specifies a Typer CLI; `pyproject.toml` carries a `TODO(layer-4)`
for the `[project.scripts]` wiring.

Layer 4 adds `src/lg2m/cli.py` as a thin Typer shell over the existing pipeline, plus a small
`pipeline.validate(...)` sibling for the one command that is not a straight wrapper. The outcome:
`lg2m check | list | validate | init` work from a shell with the exit-code contract from PLAN
Section 11 (`0` clean / `1` drift or structural error / `2` usage or config error).

**Decisions made during shaping:**
- **Scope:** ship `check`, `list`, `validate`, `init` only. `gen`/scaffolding (docs/design.md Section 10) is
  deferred to a future layer 5, matching docs/design.md Section 13's build order (step 4 = `cli.py`, step 5 =
  `scaffold/*` + `gen`). No `gen` command in this layer.
- **`init`:** scaffolds a starter `lg2m.toml` only (refuses to overwrite an existing file). Skeleton
  docs/code stay with scaffold in layer 5.
- **Config discovery:** auto-discover in CWD — prefer `lg2m.toml`, fall back to `pyproject.toml`;
  `-c/--config PATH` overrides; nothing found → exit 2.
- **`validate` placement:** orchestration lives in `pipeline.validate(...) -> DriftReport` (mirrors
  `pipeline.check`), so `cli.py` stays a thin, testable shell and the logic sits where `check` lives.
- **Framework isolation stays intact:** `import lg2m.cli` must pull in no framework. The adapter is
  already imported lazily inside `pipeline.check`; `validate` calls `load_compiled` (framework-free —
  it imports the *user's* module, which imports the framework) and never imports the adapter itself.

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

**Rating:** 3 — Moderate

**Evidence:**
- One net-new module (`src/lg2m/cli.py`) + a `pipeline.validate(...)` sibling to the existing
  `pipeline.check(...)`; new `tests/test_cli.py`; a `pyproject.toml` edit (add `typer`, wire
  `[project.scripts] lg2m = "lg2m.cli:app"`).
- Heavy reuse, no new patterns: `check` wraps `pipeline.check`; `list` uses `config.loader.load`;
  rendering reuses `report.render_text`/`render_json`; config errors reuse
  `discovery.resolve.ConfigError`.
- The only net-new logic is `validate` (parse each side, confirm entry-point import, exactly one
  `@state_model`, every conditional fan-out has `[else]`) and the exit-code-2 mapping the CLI layers
  around `check`.
- No framework coupling — `import lg2m.cli` stays framework-free; real-graph tests stay gated
  `@pytest.mark.langgraph`.

**Model Recommendation:** Sonnet.
**Reason:** Mechanical wrapping with clear reuse; the one spot needing care is `validate`'s
reuse-vs-rebuild decision for the `[else]`/state-model checks (the diff engine emits `MISSING_ELSE`
only inside `reconcile`, so `validate` derives it from `gm.routes` directly).

---

## Task 1: Save Spec Documentation

- [x] Create `agent-os/specs/2026-06-14-2225-cli-typer/` with `plan.md` (this plan), `shape.md`,
  `standards.md`, `references.md`, and `visuals/`.
- [x] `shape.md` records the four shaping decisions (scope = no `gen`; `init` = toml only; config
  auto-discovery; `validate` lives in `pipeline.py`) and the exit-code mapping table.
- [x] `standards.md` records which standards apply and how they show up (repo convention: summary +
  pointers, not full bodies).
- [x] `references.md` points at the prior spec and the reused pipeline/report/loader symbols.

### Done when
- [x] All five entries exist; the four markdown files are non-empty.
- [x] `plan.md` in the spec folder matches the approved plan (Execution Protocol + Complexity + tasks).

## Task 2: `pipeline.validate(...)` + framework-free tests

Add `validate(config_path, graph_id, *, strict=False) -> DriftReport` to `src/lg2m/pipeline.py`,
mirroring `check` but lighter — it never reconciles and never imports the adapter.

- [x] Load + resolve like `check` (`config_loader.load`, `resolve`); reuse `_usage_report` for an
  unknown `graph_id` (defensive; the CLI pre-checks membership).
- [x] Doc side: read + parse the markdown (guard a missing file → DIAGNOSTIC error), build it with
  `assemble_doc_model(parse_markdown(...))`; seed the report with
  `diagnostics_report(graph_id, doc, strict=strict)` to fold doc-side parse diagnostics.
- [x] Entry point imports: `load_compiled(resolved)`; if `loaded.compiled is None`, fold
  `loaded.diagnostics` (the `IMPORT_FAILURE`) into the report via a `GraphModel(origin="code")`.
- [x] Every conditional fan-out has `[else]`: scan `doc.routes` for empty `else_target` → add a
  `MISSING_ELSE` `DriftItem` (doc_loc). **Deviation:** the code-side AST-router scan was dropped as
  dead code — `lg2m.router` rejects a missing `[else]` at construction, so a code-side missing
  `[else]` makes the module fail to import and is already reported as `IMPORT_FAILURE`. Documented in
  the `validate` docstring.
- [x] Exactly one `@state_model`: when import succeeded, count `registry.models` with
  `is_graph_state` from `gather_annotations`; `0` or `>1` → a `STATE_MODEL_MISMATCH` ERROR item.
- [x] Reuse `DriftItem` / `DriftReport` / `DriftCategory` / `Severity` / `HINTS` so `render_text` /
  `render_json` / `exit_code` work unchanged (via the `_drift` helper).

### Done when
- [x] `./.venv/bin/python -m pytest tests/test_pipeline.py -k validate --no-cov -q` passes (new
  cases): a clean graph → `is_clean`, `exit_code == 0`; a doc missing `[else]` → a `MISSING_ELSE`
  item, `exit_code == 1`; a bad entry point → an `IMPORT_FAILURE`/`DIAGNOSTIC` item, `exit_code == 1`.
- [x] A framework-free test covers the doc-side-only path (missing `[else]` with import skipped).
- [x] Hermetic check still holds: `python -c "import sys, lg2m.pipeline; assert 'langgraph' not in sys.modules"`.
- [x] `./.venv/bin/ruff check src tests` clean.

## Task 3: `cli.py` — Typer app + four commands

Create `src/lg2m/cli.py` with `from __future__ import annotations`, `app = typer.Typer(...)`, and
shared helpers. Keep the import framework-free (Typer only; pipeline imports pull in no framework).

- [x] Shared helpers:
  - `_resolve_config(config: Path | None) -> Path` — return `config` if given; else CWD `lg2m.toml`,
    then CWD `pyproject.toml`; none found → `raise typer.Exit(2)` with a clear message.
  - `_load_graphs(path) -> dict` — wraps `config_loader.load`; catches `FileNotFoundError` and the
    TOML decode error → exit 2.
  - `_resolve_graph_id(graphs, graph_id) -> str` — explicit id present → return it; id absent and
    exactly one graph → return it; unknown id or ambiguous (0 / >1 with no id) → exit 2 listing the
    available graph ids.
  - `_emit(report, fmt, no_prose)` — optionally drop `PROSE_DRIFT` items, then print
    `render_text(report)` or `render_json(report)`. (A shared `_fail(message) -> NoReturn` centralizes
    the exit-2 message+raise.)
- [x] `check [GRAPH_ID] [-c/--config PATH] [--format text|json] [--strict] [--no-prose]`:
  resolve config + graphs + graph_id (exit 2 on usage/config); `try: report = check(path, gid,
  strict=strict) except ConfigError: raise typer.Exit(2)`; `_emit`; `raise typer.Exit(report.exit_code)`.
  (Import failure of the user's graph stays exit 1 via `report.exit_code`.)
- [x] `validate [GRAPH_ID] [-c/--config PATH] [--format text|json] [--strict]`: same resolution,
  then `pipeline.validate(...)`; `_emit`; exit `report.exit_code`; `ConfigError` → exit 2.
- [x] `list [-c/--config PATH] [--format text|json]`: resolve config + graphs; print each
  `graph_id` with its `graph` and `markdown` (text) or a JSON object; exit 0.
- [x] `init [-c/--config PATH]`: target = `config` or CWD `lg2m.toml`; if it exists → exit 2
  (refuse overwrite); else write the starter template (one commented
  `[tool.lg2m.graphs.<id>]` block with `graph`/`markdown`/`sys_path`/`xray`); print the path; exit 0.

### Done when
- [x] `import lg2m.cli` succeeds and imports no framework:
  `python -c "import sys, lg2m.cli; assert 'langgraph' not in sys.modules and 'langchain_core' not in sys.modules"`.
- [x] The CLI `--help` lists `check`, `list`, `validate`, `init` and no `gen`.
- [x] `./.venv/bin/ruff check src tests` clean.

## Task 4: Wire `pyproject.toml`, CLI tests, and the suite gate

- [x] `pyproject.toml`: add `typer` to `dependencies`; replace the `TODO(layer-4)` comment with
  `[project.scripts]` `lg2m = "lg2m.cli:app"`. Reinstall editable so the `lg2m` entry point exists.
- [x] `tests/test_cli.py` with Typer's `CliRunner` (framework-free unless marked):
  - `list` against `examples/support_pipeline/lg2m.toml` → exit 0, names `support_pipeline`.
  - `check`/`validate` with an unknown graph id → exit 2; with a missing config file → exit 2;
    with malformed TOML → exit 2; with a `ConfigError` (bad `graph=`) → exit 2; no config found → 2.
  - `init` writes a file and refuses to overwrite (exit 2) — use `tmp_path`.
  - default-graph-id omission works when the config has exactly one graph.
  - `--format json` emits parseable JSON; `--no-prose` drops `PROSE_DRIFT` items (unit test of `_emit`).
  - `@pytest.mark.langgraph`: `check support_pipeline` against the real graph → exit 0, clean.
- [x] Confirm `check` writes nothing (docs/design.md Section 14: assert no files created during a `check` run).

### Done when
- [x] `./.venv/bin/python -m pytest -q` all green (incl. `@langgraph`); 90% coverage gate holds
  (165 passed, 96.87%).
- [x] `./.venv/bin/python -m pytest -q -m "not langgraph"` green (154 passed, framework-free, 93.67%).
- [x] `./.venv/bin/ruff check src tests` clean.
- [x] `./.venv/bin/lg2m check support_pipeline -c examples/support_pipeline/lg2m.toml` exits 0 and
  prints a clean report; a deliberately drifted markdown copy exits 1; an unknown id exits 2.

---

## Critical Files

- **New:** `src/lg2m/cli.py`, `tests/test_cli.py`.
- **Edited:** `src/lg2m/pipeline.py` (add `validate`), `pyproject.toml` (add `typer`; add
  `[project.scripts]`), `tests/test_pipeline.py` (validate cases).
- **Reused unchanged:**
  - `lg2m.pipeline.check`, `gather_annotations`, `_usage_report` (`src/lg2m/pipeline.py`)
  - `lg2m.report.render_text` / `render_json` and `DriftReport.exit_code` (`src/lg2m/report/`)
  - `lg2m.config.loader.load` (`src/lg2m/config/loader.py`)
  - `lg2m.discovery.resolve.resolve` + `ConfigError` (`src/lg2m/discovery/resolve.py`)
  - `lg2m.diff.assemble.assemble_doc_model`, `lg2m.diff.engine.diagnostics_report`,
    `lg2m.diff.categories.{DriftCategory,Severity,HINTS,default_severity}`,
    `lg2m.introspect.loader.load_compiled`, `lg2m.parsing.markdown.parse_markdown` (for `validate`)
- **Read-only oracle:** `examples/support_pipeline/` (clean graph + `lg2m.toml`).

## Exit-code mapping (the contract the CLI enforces)

| Situation | Exit | Where it's mapped |
|---|---|---|
| Clean report | 0 | `report.exit_code` |
| Drift / structural error (incl. user-graph `IMPORT_FAILURE`) | 1 | `report.exit_code` |
| No config found / file missing / malformed TOML | 2 | `_resolve_config` / `_load_graphs` |
| Unknown or ambiguous `graph_id` | 2 | `_resolve_graph_id` |
| `ConfigError` from `resolve` (bad `graph=`/`markdown=`) | 2 | `try/except ConfigError` around `check`/`validate` |
| `init` target already exists | 2 | `init` overwrite guard |

## Verification

```bash
source .venv/bin/activate
pip install -e '.[langgraph]'                          # picks up typer + the lg2m script
python -m pytest -q                                    # all green incl. @langgraph; 90% gate holds
python -m pytest -q -m "not langgraph"                 # CLI tests run framework-free
ruff check src tests                                   # clean
python -c "import sys, lg2m.cli; assert 'langgraph' not in sys.modules"   # framework isolation

lg2m list -c examples/support_pipeline/lg2m.toml                          # -> support_pipeline, exit 0
lg2m check support_pipeline -c examples/support_pipeline/lg2m.toml        # -> clean, exit 0
lg2m check support_pipeline -c examples/support_pipeline/lg2m.toml --format json
lg2m validate support_pipeline -c examples/support_pipeline/lg2m.toml     # -> exit 0
lg2m check nope -c examples/support_pipeline/lg2m.toml; echo $?           # -> 2
lg2m init -c /tmp/lg2m-init-smoke/lg2m.toml                               # -> writes template, exit 0
```
