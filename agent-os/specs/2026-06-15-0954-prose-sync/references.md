# References for lg2m sync (prose write-back)

## Design of record

- **`docs/prose-sync.md`** — the authoritative design note for this feature (the model, the four
  cases, the baseline, the edge problem, the normalization rationale, the four decisions).
- **`docs/design.md` Section 12** (prose sync, deferred from v1) and **Section 14** (`check` writes nothing
  — the invariant `sync` must not break).
- **`agent-os/product/roadmap.md` → Future → Prose sync (`lg2m sync`)** — product-level scope.

## Prior specs to mirror (format + patterns)

### CLI layer — `agent-os/specs/2026-06-14-2225-cli-typer/`

- **Relevance:** the `@app.command()` skeleton and exit-code discipline `sync` copies.
- **Key patterns:** module-level `typer.Option`/`Argument` constants (ruff B008); `_resolve_config`
  / `_load_graphs` / `_resolve_graph_id` / `_fail` (stderr + `raise typer.Exit(2)`); exit codes
  `0`/`1`/`2`; `CliRunner` tests.

### Scaffold/gen layer — `agent-os/specs/2026-06-14-2301-scaffold-gen/`

- **Relevance:** `gen --from-doc` ("existing prose preserved") and `gen --from-code` ("prose as
  TODO") are the one-shot version of `sync`; the bootstrap directional-adopt rule is their
  incremental form. Phased-plan format with `### Done when` blocks.
- **Key patterns:** `_write_text` / `_write_files` refuse-to-overwrite; tmp_path write tests.

## Code reuse map

### New (`src/lg2m/sync/`)
`__init__.py` (exports `run_sync`, `SyncResult`), `normalize.py`, `lockfile.py`, `merge.py`,
`write_py.py`, `write_md.py`, `engine.py`.

### Edited
- `src/lg2m/annotations/reader.py` — extend `AnnoRef` (`docstring`, `doc_span`, `body_col`); capture
  in the decorator classifier; stays `ast`-only / import-free.
- `src/lg2m/pipeline.py` — `gather_annotations` also returns a `prose` map keyed `(kind, key)`.
- `src/lg2m/diff/assemble.py` — `assemble_code_model` sets `Node`/`Predicate` docstrings from the map
  (replacing the always-`None` pass-through).
- `src/lg2m/diff/engine.py` — `_check_prose` uses `sync.normalize.prose_equal` and covers predicates.
- `src/lg2m/parsing/markdown.py` — export `is_prose_line` (factored from `_extract_prose`).
- `src/lg2m/cli.py` — new `sync` command + option constants.

### Reused unchanged (with why)
- `src/lg2m/cli.py` — `_resolve_config` (l.65), `_load_graphs` (l.78), `_resolve_graph_id` (l.85),
  `_fail` (l.107): config resolution + exit-2 path.
- `src/lg2m/parsing/markdown.py` — `parse_markdown` → `MarkdownDoc.entities`; `Entity(id, section,
  start, end, lines, prose)` carries clean `.prose` + 0-based `start`/`end` spans (end exclusive) for
  write-back targeting.
- `src/lg2m/annotations/reader.py` — `read_file` (returns annotations; sync calls it directly for
  code-side prose + spans).
- `src/lg2m/diff/categories.py` — `DriftCategory.PROSE_DRIFT` (WARNING, report-only) + `HINTS`.
- `src/lg2m/ir.py` — `Node` / `Predicate` already carry `prose` + `docstring` (`field(compare=False)`,
  so identity-agnostic). `SourceLocation(file, line, col)` has no end span — the writers compute
  spans transiently; do not add an end span to the IR.
- `src/lg2m/parsing/meta.py` — `parse_entity_meta` separates TABLE / FENCE / NOTE from prose.

### Test fixtures
- `examples/support_pipeline/` (copied into `tmp_path` for the e2e). `nodes.py` has a module
  docstring + one function docstring (`escalate_to_human`); the other ~12 `@node` functions have
  none, while `docs/support_pipeline.md` carries prose for every entity — the case the
  directional-adopt bootstrap targets.
- `tests/conftest.py` — `golden_toml_path`, autouse `reset_registry`; `_drop_example_modules` import
  hygiene in `tests/test_cli.py`. `@pytest.mark.langgraph` is **not** needed by sync tests
  (framework-free).
