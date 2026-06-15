# References — lg2m layer 4

## The pipeline the CLI wraps

- `src/lg2m/pipeline.py` — `check(config_path, graph_id, *, strict=False) -> DriftReport` (the
  orchestrator the `check` command wraps); `gather_annotations(package_dir)` (AST reader over the
  package's source, reused by the new `validate`); `_usage_report(graph_id, message)` (the
  unknown-graph helper). `validate(...)` is added here, mirroring `check`.
- `src/lg2m/report/__init__.py` — `render_text(report) -> str`, `render_json(report, *, indent=2)
  -> str`, and `DriftReport` (`.exit_code` 0/1, `.is_clean`, `.has_errors`, `.items`, `.errors`,
  `.warnings`). The CLI renders and exits on these.
- `src/lg2m/report/model.py` — `DriftReport.exit_code` returns `1` on any ERROR, else `0`; the CLI
  owns the `2` for usage/config.

## Config + discovery (usage/config exit-2 sources)

- `src/lg2m/config/loader.py` — `load(path) -> dict[str, dict]` (the `[tool.lg2m.graphs.*]`
  mapping). Powers `list` and the CLI's pre-flight membership check. Raises on a missing file /
  malformed TOML — the CLI catches these and maps them to exit 2.
- `src/lg2m/discovery/resolve.py` — `resolve(cfg, *, base_dir, graph_id) -> ResolvedGraph` and
  `ConfigError` (raised on a bad `graph=`/`markdown=`; the CLI maps it to exit 2).

## Parsers + diff used by `validate`

- `src/lg2m/parsing/markdown.py` — `parse_markdown(text, *, file=...)`.
- `src/lg2m/diff/assemble.py` — `assemble_doc_model(doc, *, file=...) -> GraphModel` (doc side, with
  `routes` to scan for `[else]`).
- `src/lg2m/diff/engine.py` — `diagnostics_report(graph_id, gm, *, strict=False) -> DriftReport`
  (folds a single side's diagnostics; used to seed `validate`'s report).
- `src/lg2m/diff/categories.py` — `DriftCategory` (`MISSING_ELSE`, `STATE_MODEL_MISMATCH`,
  `DIAGNOSTIC`), `Severity`, `HINTS`, `default_severity`.
- `src/lg2m/introspect/loader.py` — `load_compiled(resolved) -> LoadedGraph` (`.compiled`,
  `.diagnostics`); the "entry point imports" check. Framework-free (the user's module pulls in
  langgraph, not this module).
- `src/lg2m/annotations/registry.py` — `Registry`/`ModelEntry.is_graph_state`/`RouterEntry.else_target`
  (the shape `gather_annotations` returns; `validate` counts state models and scans routers).

## Tests + fixtures

- `tests/conftest.py` — `golden_toml_path`, `golden_md_text`, `golden_compiled`, autouse
  `reset_registry`; prepends `src/` to `sys.path`.
- `tests/test_pipeline.py` — the existing `check` end-to-end and import-failure patterns the new
  `validate` tests mirror (`_drop_example_modules`, the `tmp_path` config builder).

## Design of record

- `docs/design.md` Section 11 (CLI surface + exit codes), Section 10 (scaffold — the deferred layer 5),
  Section 13 (build order: step 4 = `cli.py`), Section 14 (test strategy: CliRunner exit codes,
  `check` writes nothing), Section 12 (limitations).
- Prior spec: `agent-os/specs/2026-06-14-2146-langgraph-introspect-pipeline/` (layer 3 — the real
  introspector + `check`).
- Approved plan snapshot: `~/.claude/plans/dazzling-stargazing-tide.md`.
