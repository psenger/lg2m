# Typer CLI over the check pipeline — lg2m layer 4 (shape)

**Spec folder:** `agent-os/specs/2026-06-14-2225-cli-typer/`

## Scope

Layer 4 gives lg2m its user-facing entry point: a Typer CLI (`src/lg2m/cli.py`) wired as
`[project.scripts] lg2m = "lg2m.cli:app"`. It is a thin shell over the already-green pipeline —
`pipeline.check`, `report.render_text`/`render_json`, `config.loader.load`,
`discovery.resolve.resolve` — plus one new orchestrator, `pipeline.validate`, for the lighter
`validate` command.

**In scope:** the `check`, `list`, `validate`, `init` commands; the `0`/`1`/`2` exit-code contract
(docs/design.md Section 11); `--format text|json`, `--strict`, `--no-prose`, `-c/--config`; config
auto-discovery; `tests/test_cli.py` (CliRunner) with a `@pytest.mark.langgraph` end-to-end.

**Out of scope (deferred to layer 5):** `gen --from-doc | --from-code` and `scaffold/`
(docs/design.md Section 10). No `gen` command, not even a stub, ships in this layer — matching
docs/design.md Section 13's build order (step 4 = `cli.py`, step 5 = `scaffold/*` + `gen`).

## Decisions

1. **Scope = no `gen`.** Ship `check`/`list`/`validate`/`init` only; scaffolding is its own layer.
   Keeps layer 4 a wrapper, not a code generator.
2. **`init` writes a starter `lg2m.toml` only** — one commented `[tool.lg2m.graphs.<id>]` block
   (`graph`/`markdown`/`sys_path`/`xray`). It refuses to overwrite an existing file (exit 2). Skeleton
   docs/code belong with `gen`/scaffold (layer 5).
3. **Config auto-discovery.** Commands take `-c/--config PATH`. With no flag, discover in the CWD:
   prefer `lg2m.toml`, fall back to `pyproject.toml`. Nothing found → exit 2. No walking up parents
   (avoids picking up an unexpected ancestor config).
4. **`validate` orchestration lives in `pipeline.validate(...) -> DriftReport`**, mirroring
   `pipeline.check`, so `cli.py` stays a thin, easily testable Typer shell and the logic sits beside
   `check`. `validate` is lighter than `check`: it parses each side, confirms the entry point imports,
   asserts exactly one `@state_model`, and asserts every conditional fan-out has an `[else]`. It does
   **not** reconcile and **never imports the framework adapter**.
5. **Framework isolation holds.** `import lg2m.cli` pulls in no framework (verified by the existing
   hermetic-subprocess style check). `pipeline.check` already lazy-imports the adapter; `validate`
   only calls `load_compiled` (which imports the *user's* module, not langgraph directly).
6. **Default `graph_id`.** When the config declares exactly one graph, `GRAPH_ID` may be omitted on
   `check`/`validate`. Zero graphs, or more than one with no id, → exit 2 listing the available ids.

## `validate` derivation notes

- The diff engine emits `MISSING_ELSE` only inside `reconcile`. `validate` does not reconcile, so it
  scans `doc.routes` (from `assemble_doc_model`) and the AST-recovered code routers (from
  `gather_annotations`) directly for an empty `else_target`.
- "Exactly one `@state_model`" is a code-side fact, counted from `gather_annotations`' registry
  (`ModelEntry.is_graph_state`) — robust even though the example's predicates are not "live"
  (the Model-A router resolves names lazily; the AST reader sees every annotation in source).
- The code-side annotation checks run only when the entry point imported successfully; on
  `IMPORT_FAILURE` that error dominates the report.

## Exit-code mapping (the contract the CLI enforces)

| Situation | Exit | Where it's mapped |
|---|---|---|
| Clean report | 0 | `report.exit_code` |
| Drift / structural error (incl. user-graph `IMPORT_FAILURE`) | 1 | `report.exit_code` |
| No config found / file missing / malformed TOML | 2 | `_resolve_config` / `_load_graphs` |
| Unknown or ambiguous `graph_id` | 2 | `_resolve_graph_id` |
| `ConfigError` from `resolve` (bad `graph=`/`markdown=`) | 2 | `try/except ConfigError` around `check`/`validate` |
| `init` target already exists | 2 | `init` overwrite guard |

## Quality gates

**Per-task Definition of Done.** Every task in `plan.md` ends with a `### Done when` checklist of
concrete commands/checks (pytest subsets pass, ruff clean, exit codes correct, framework isolation
holds). No separate acceptance-criteria section.

## Context

- **Visuals:** none.
- **References:** see `references.md` — the reused pipeline/report/loader symbols and the prior
  layer-3 spec.
- **Product alignment:** docs/design.md Section 13 build order — this is step 4 (`cli.py`); `gen`/scaffold is
  step 5.
- **Complexity:** Rating 3 (Moderate); model Sonnet. Tasks + subtasks, no phases.
