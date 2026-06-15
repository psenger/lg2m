# lg2m Layer 6 — `lg2m sync` CLI command (Phase 6 wiring)

## Context

The prose-sync engine (Phases 1–5, spec `2026-06-15-0954-prose-sync`, Tasks 1–6) is fully
shipped and green. `run_sync()` in `src/lg2m/sync/engine.py` handles merge decisions,
surgical write-back to both docstrings and Markdown, the `.lg2m.lock` baseline, and
`--dry-run`. All six sync sub-modules are at 100% test coverage.

The only remaining work is Phase 6 (Tasks 7.1–7.2 from the prior spec): wiring `sync`
as a Typer CLI command and adding end-to-end tests that verify the full workflow on a
real example graph.

Intended outcome: `lg2m sync` is a callable CLI command that converges docstrings and
Markdown prose for a configured graph, updates `.lg2m.lock`, and exits 0 on clean / 1
on unresolved conflicts.

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

**Rating:** 2 — Simple

**Evidence:**
- One new `@app.command()` in `cli.py` (~25 lines, exact pattern of `gen()`)
- One new `Prefer(str, enum.Enum)` with two values (`code`, `doc`)
- `SyncResult` rendered with inline `typer.echo()` calls — no new module needed
- `tests/test_cli_sync.py` mirrors `tests/test_cli_gen.py` structure exactly
- `tests/test_sync_e2e.py` copies `examples/support_pipeline/` into `tmp_path`
- No new design decisions; `run_sync()` is complete and 100%-tested

**Model Recommendation:** Sonnet
**Reason:** Purely additive CLI wiring on established patterns with no architectural unknowns.

---

## Task 1: Save Spec Documentation

- [x] Create `agent-os/specs/2026-06-15-1416-sync-cli-verb/` containing `plan.md` (this file), `shape.md`, `standards.md`, `references.md`, and an empty `visuals/` directory.
  - **`shape.md`** — scope: "add `sync` command to `cli.py` (Task 7.1–7.2 from spec `2026-06-15-0954-prose-sync`)"; decisions: inline rendering via `typer.echo()` (no new render module), `Prefer` enum follows `OutputFormat` pattern (`(str, enum.Enum)` subclass), `--lock` option passes through to `run_sync(lock_path=)`, optional `Prefer` typed as `Prefer | None` with default `None`; visuals: none; references: prior spec, `tests/test_cli_gen.py`, `src/lg2m/sync/engine.py`; standards applied: `ir/identity`, `ir/mutability`, `global/coding-conventions`, `global/tdd-workflow`.
  - **`standards.md`** — paste full content of `agent-os/standards/ir/identity.md`, `agent-os/standards/ir/mutability.md`, `agent-os/standards/global/coding-conventions.md`, `agent-os/standards/global/tdd-workflow.md`.
  - **`references.md`** — pointers to: `agent-os/specs/2026-06-15-0954-prose-sync/plan.md` (prior spec, Tasks 7.1–7.2 are the source of truth for the command contract); `src/lg2m/cli.py` (gen() and check() patterns to mirror); `tests/test_cli_gen.py` (CliRunner test pattern); `src/lg2m/sync/engine.py` (`SyncResult` fields and `run_sync()` signature); `examples/support_pipeline/` (e2e fixture source).

---

## Tasks

- [x] **`cli.py` — `Prefer` enum.** Add `class Prefer(str, enum.Enum): code = "code"; doc = "doc"` near the existing `OutputFormat` enum (same pattern: `(str, enum.Enum)` subclass).

- [x] **`cli.py` — option constants.** Add three module-level `typer.Option` constants (B008 pattern, near `_FORMAT_OPT`):
  ```python
  _PREFER_OPT = typer.Option(None, "--prefer", help="conflict resolution: code or doc")
  _DRY_RUN_OPT = typer.Option(False, "--dry-run", help="report without writing files")
  _LOCK_OPT = typer.Option(None, "--lock", help="override default .lg2m.lock path")
  ```

- [x] **`cli.py` — import.** Add `from lg2m.sync import run_sync` to the import block.

- [x] **`cli.py` — `sync` command.** Add the command function:
  - Signature: `graph_id: str | None = _GRAPH_ID_ARG`, `config: Path | None = _CONFIG_OPT`, `prefer: Prefer | None = _PREFER_OPT`, `dry_run: bool = _DRY_RUN_OPT`, `lock: Path | None = _LOCK_OPT`.
  - Body: `_resolve_config` → `_load_graphs` → `_resolve_graph_id` → call `run_sync(path, gid, prefer=prefer.value if prefer else None, dry_run=dry_run, lock_path=lock)` → render → `raise typer.Exit(result.exit_code)`.
  - Catch `ConfigError` → `_fail(...)` (exit 2).

- [x] **`cli.py` — `SyncResult` rendering** (inline in `sync()`, no helper function). Output format:
  - Summary line: `f"{'(dry run) ' if dry_run else ''}{gid}: {len(result.code_written) + len(result.md_written)} written, {len(result.adopted)} adopted, {len(result.unresolved)} unresolved"`
  - Per-entity lines with 10-char left-aligned label:
    - `"  code:     {kind}:{key}"` for each `(kind, key)` in `result.code_written`
    - `"  doc:      {kind}:{key}"` for each in `result.md_written`
    - `"  adopted:  {kind}:{key}"` for each in `result.adopted`
    - `"  conflict: {kind}:{key}"` for each in `result.conflicts`
    - `"  skipped:  {kind}:{key}  (raw prefix)"` for each in `result.raw_prefix_skips`
    - `"  skipped:  {kind}:{key}  (interleaved)"` for each in `result.interleaved_skips`
  - If `result.lock_written`: `"  lock:     updated"`
  - Unresolved items go to `typer.echo(..., err=True)` so stdout stays machine-readable.

- [x] **`tests/test_cli_sync.py`** — new file, `CliRunner`-driven (mirrors `tests/test_cli_gen.py`). Use fixtures that build a minimal `tmp_path` setup (one-node Markdown + stub Python file). Cases:
  - `--dry-run` with a bootstrap case (MD has prose, code has no docstring) → exit 0, no files mutated, output contains "(dry run)"
  - Clean bootstrap run (no `--dry-run`) → exit 0, output shows `"code: node:..."`, `.lg2m.lock` created
  - Second run (lock written, no change) → exit 0, "0 written"
  - Unresolved conflict (both sides changed since lock) → exit 1, `"conflict: node:..."` in stderr
  - `--prefer doc` on the same conflict → exit 0, code overwritten
  - Bad config path → exit 2

- [x] **`tests/test_sync_e2e.py`** — new file, exercises `run_sync()` directly (not through CLI) on a `tmp_path` copy of `examples/support_pipeline/`. Cases:
  - Drift one node's Markdown prose → `run_sync()` → assert the docstring matches `normalize_prose(new_md_prose)`
  - Drift one predicate's docstring → `run_sync()` → assert the Markdown prose matches `normalize_prose(new_docstring)`
  - `run_sync()` again without changes → `result.wrote_files` is False, `.lg2m.lock` bytes unchanged
  - After a clean sync, `pipeline.check()` (framework-free path, entry point that fails to import is acceptable) or directly `diff/engine` → no `PROSE_DRIFT` items in the result

### Done when
- [x] `python -m pytest tests/test_cli_sync.py tests/test_sync_e2e.py --no-cov -q` green
- [x] `python -m pytest -q` passes the 90% coverage gate
- [x] `ruff check src tests` clean

---

## Key files

| File | Action |
|------|--------|
| `src/lg2m/cli.py` | Add `Prefer` enum, three option constants, import, `sync` command |
| `tests/test_cli_sync.py` | New — CliRunner tests for `sync` command |
| `tests/test_sync_e2e.py` | New — end-to-end on `examples/support_pipeline/` copy |
| `agent-os/specs/2026-06-15-1416-sync-cli-verb/` | New — spec docs (Task 1) |

**Reused unchanged:** `_resolve_config`, `_load_graphs`, `_resolve_graph_id`, `_fail` in `cli.py`; all of `src/lg2m/sync/` (engine, merge, lockfile, normalize, write_py, write_md).

## Standards

@agent-os/standards/ir/identity.md
@agent-os/standards/ir/mutability.md
@agent-os/standards/global/coding-conventions.md
@agent-os/standards/global/tdd-workflow.md

## Verification

```bash
# Focused (after each task)
python -m pytest tests/test_cli_sync.py tests/test_sync_e2e.py --no-cov -q

# Full gate (before marking complete)
python -m pytest -q
ruff check src tests
```
