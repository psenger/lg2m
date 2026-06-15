# sync CLI command — Shaping Notes

## Scope

Add `sync` command to `cli.py` (Task 7.1–7.2 from spec `2026-06-15-0954-prose-sync`).
The sync engine, merge logic, surgical writers, and lockfile are all complete and
100%-tested. This is purely CLI wiring.

## Decisions

- **Inline rendering:** `SyncResult` output rendered with inline `typer.echo()` calls
  inside `sync()` — no new render module. The result structure is simple enough that
  a dedicated renderer would add indirection without value.
- **`Prefer` enum:** follows `(str, enum.Enum)` pattern of `OutputFormat`. Values:
  `code = "code"`, `doc = "doc"`. Typed as `Prefer | None` with default `None` so the
  option is omitted when not needed.
- **`--lock` option:** passes through to `run_sync(lock_path=)` verbatim. Default `None`
  lets the engine use `config_path.parent / ".lg2m.lock"`.
- **Unresolved items to stderr:** `conflict:`, `skipped:` lines go to
  `typer.echo(..., err=True)` so stdout is machine-readable.
- **Exit codes:** 0 = synced-or-clean, 1 = unresolved conflict/skip (from
  `result.exit_code`), 2 = usage/config error (via `_fail()`).

## Context

- **Visuals:** None (CLI output, no UI mockup needed)
- **References:** `agent-os/specs/2026-06-15-0954-prose-sync/plan.md` (Tasks 7.1–7.2);
  `src/lg2m/cli.py` (gen() and check() patterns); `tests/test_cli_gen.py` (CliRunner
  pattern); `src/lg2m/sync/engine.py` (SyncResult, run_sync);
  `examples/support_pipeline/` (e2e fixture source)
- **Product alignment:** The sync verb is the write-back counterpart to `check`'s
  read-only PROSE_DRIFT report; it completes the bidirectional prose reconciliation
  described in the product mission.

## Standards Applied

- `ir/identity` — no IR changes in this task; confirms we don't accidentally add
  identity fields
- `ir/mutability` — confirms `SyncResult` (mutable dataclass) follows the mutable-
  container pattern
- `global/coding-conventions` — import order, one component per file
- `global/tdd-workflow` — tests written alongside implementation; focused pytest runs
  before full suite
