# References for sync CLI command

## Prior Spec

### prose-sync (Tasks 7.1–7.2)

- **Location:** `agent-os/specs/2026-06-15-0954-prose-sync/plan.md`
- **Relevance:** The source of truth for the `sync` command contract — Tasks 7.1 and
  7.2 define the CLI signature, option names, exit codes, and e2e test cases.
- **Key patterns:** `--prefer` enum, `--dry-run`, `--lock` option; CliRunner test
  structure; `run_sync()` call with `prefer.value if prefer else None`.

## CLI Patterns to Mirror

### `gen()` command (existing)

- **Location:** `src/lg2m/cli.py` lines 210–229
- **Relevance:** The `sync` command follows the same structure: resolve config → load
  graphs → resolve graph ID → call engine → render output → exit.
- **Key patterns:** `_resolve_config` / `_load_graphs` / `_resolve_graph_id` / `_fail`;
  module-level `typer.Option` constants (B008); `raise typer.Exit(code)`.

### `check()` command (existing)

- **Location:** `src/lg2m/cli.py` lines 137–153
- **Relevance:** Shows how `ConfigError` is caught and how exit codes map to outcomes.

## CLI Test Pattern

### `test_cli_gen.py`

- **Location:** `tests/test_cli_gen.py`
- **Relevance:** CliRunner fixture pattern, `_mini_config()` helper, exit-code
  assertions, stdout content checks.
- **Key patterns:** `runner.invoke(app, ["sync", "-c", str(cfg)])` for command
  invocation; `assert result.exit_code == N`; file-mutation checks after invocation.

## Sync Engine

### `run_sync()` and `SyncResult`

- **Location:** `src/lg2m/sync/engine.py`
- **Relevance:** `SyncResult` fields (`code_written`, `md_written`, `adopted`,
  `conflicts`, `raw_prefix_skips`, `interleaved_skips`, `lock_written`); computed
  properties `unresolved`, `exit_code`, `wrote_files`.
- **Key patterns:** `run_sync(config_path, graph_id, *, prefer, dry_run, lock_path)`.

## E2E Fixture Source

### `support_pipeline` example

- **Location:** `examples/support_pipeline/`
- **Relevance:** A realistic multi-file LangGraph package with `@node` and `@predicate`
  annotations, Markdown contract, and `lg2m.toml` config. Used as the fixture for
  end-to-end sync tests by copying into `tmp_path`.
- **Key patterns:** `nodes.py` has 12 `@node` annotations (only `escalate_to_human`
  has a pre-existing docstring that conflicts with the MD prose); `predicates.py` has
  2 `@predicate` annotations with no docstrings; first sync with `prefer="doc"` resolves
  the conflict and bootstraps all others.
