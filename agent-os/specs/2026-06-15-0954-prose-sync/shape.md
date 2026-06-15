# lg2m sync (prose write-back) — Shaping Notes

## Scope

A new write-only CLI verb `lg2m sync` that reconciles the **free-prose slice** of each
node/predicate between the Markdown `### entity` paragraph and the function docstring, using a
committed per-entity `.lg2m.lock` baseline so the two-way sync is safe. `check` stays read-only
(docs/design.md Section 14) and keeps reporting `PROSE_DRIFT`; `sync` is the only verb allowed to write prose
across the boundary. Design of record: `docs/prose-sync.md`, docs/design.md Section 12.

This is the first lg2m verb that mutates user `.py` source.

## Decisions

- **Edges:** Markdown-only. Edges have no docstring home in code, so nothing to sync. `sync` touches
  nodes + predicates only.
- **Baseline storage:** committed repo-root `.lg2m.lock` (JSON, stdlib only), per-graph/per-entity
  `base_hash` of last-synced *normalized* prose. Per-entity value is an object so a future
  `base_text` (true 3-way) can be added without a format break.
- **Conflict policy:** refuse + show diff by default; `--prefer code|doc` resolves; exit 1 on any
  unresolved conflict.
- **Doc write mechanism:** targeted source-span edit (stdlib only) — replace only the docstring
  node's line span, re-indent to the function body, leave the rest of the file byte-identical. No
  `ast.unparse` round-trip.
- **Bootstrap (no lock yet): directional adopt.** One side empty + other has prose → write the
  non-empty side into the empty side (the incremental form of `gen --from-doc`/`--from-code`); both
  present & equal → adopt silently; both present & unequal → conflict. Chosen because the real
  example (`examples/support_pipeline/`) has Markdown prose for all entities but docstrings on only
  one function, so a strict "any no-base difference is a conflict" rule would refuse ~12 of 15
  entities on the first run.
- **Scope of "prose":** only the free-prose slice crosses into code. Structured-meta (GFM table /
  `<!-- lg2m -->` fence — introspection-owned) and `> Note:` (human-only) never enter a docstring.
- **Framework-free invariant (stronger than `check`):** `sync` imports no framework even at runtime;
  prose lives in source text + Markdown, neither needs a compiled graph. The AST reader still never
  imports the target module.

### Foundational gap found during shaping
The code side captures **no docstrings today** — `annotations/reader.py` stops at the decorator
line, so `Node.docstring`/`Predicate.docstring` are always `None` and `diff/engine._check_prose`
never fires. Adding docstring capture (reader → pipeline → assemble) is Phase 1 of this work, and it
incidentally makes `check`'s `PROSE_DRIFT` real for both nodes and predicates.

## Context

- **Visuals:** None.
- **References:** `docs/prose-sync.md` (design of record); prior specs
  `agent-os/specs/2026-06-14-2225-cli-typer/` and `.../2026-06-14-2301-scaffold-gen/` (format + CLI
  and gen patterns to mirror). Code reuse map in `references.md`.
- **Product alignment:** roadmap "Future → Prose sync (`lg2m sync`)" — matches exactly (`.lg2m.lock`
  per-entity baseline, free-prose-only, edges Markdown-only, out of scope for v1 which only reports
  `PROSE_DRIFT`). Mission's "own the source that normally drifts" extends to prose via an explicit
  baseline rather than an arbiter.

## Standards Applied

Full text in `standards.md`. Why each applies:

- `testing/testing`, `testing/mocking`, `global/tdd-workflow` — large test surface; TDD the risky
  writer (write the byte-preservation test first); mock at boundaries / use tmp copies.
- `patterns/guards`, `error-handling/error-handling` — treat the target as untrusted; refuse on
  conflict, refuse-to-overwrite posture, raw-prefix skip, exit-code discipline.
- `global/coding-conventions`, `clean-code`, `simplicity`, `value-objects` — conventions (`from
  __future__`, `str | None`, ruff E/F/I/UP/B, line 100); KISS (hash-only now, defer text 3-way);
  immutable `Lock`/`SyncResult`/`Action`.
- `ir/identity`, `ir/mutability` — touching `Node`/`Predicate` `prose`/`docstring` (`compare=False`)
  and adding new value structs.

## Key design reference

### Prose normalization (`sync/normalize.py`) — one helper, shared by `engine._check_prose` and `sync`
Canonical order: (1) CRLF/CR → LF; (2) `textwrap.dedent`; (3) drop leading blank lines; (4) per-line
`rstrip`; (5) collapse blank-line runs to one; (6) final `strip`. `prose_hash` = sha256 hex of the
normalized utf-8. `prose_equal(a,b)` = normalize-then-compare. Keep tables/fences out of docstrings;
literal tabs at line starts and fenced code blocks inside prose are the known-fragile cases.

### AST docstring capture (`annotations/reader.py`)
Extend `AnnoRef` with `docstring: str | None`, `doc_span: tuple[int,int] | None` (1-based inclusive),
`body_col: int | None`. For node/predicate decorators: `ast.get_docstring(fn, clean=False)`; if
`fn.body[0]` is `ast.Expr`→`ast.Constant[str]`, `doc_span = (expr.lineno, expr.end_lineno)`; always
`body_col = fn.body[0].col_offset`. `ast`-only; never import the target.

### `.lg2m.lock` schema (JSON, `sort_keys=True`, trailing `\n`)
```json
{ "version": 1,
  "graphs": { "<gid>": {
    "nodes":      { "<id>":   { "base_hash": "<sha256>" } },
    "predicates": { "<name>": { "base_hash": "<sha256>" } } } } }
```

### Per-entity decision table (`sync/merge.py`)
`H_code = prose_hash(docstring)`, `H_md = prose_hash(md_prose)`, `B = base_hash`.

| base | code vs base | md vs base | extra | action |
|---|---|---|---|---|
| present | changed | unchanged | — | WRITE_CODE (md→docstring) |
| present | unchanged | changed | — | WRITE_MD (docstring→md) |
| present | unchanged | unchanged | — | NOOP |
| present | changed | changed | — | CONFLICT (or `--prefer`) |
| absent | — | — | both equal (incl. both empty) | ADOPT (set base) |
| absent | — | — | one empty, other prose | ADOPT non-empty → empty (set base) |
| absent | — | — | both non-empty, unequal | CONFLICT (or `--prefer`) |

`--prefer code` → WRITE_CODE; `--prefer doc` → WRITE_MD. After any write/adopt, `set_base` to the
agreed normalized hash. Conflicts leave base untouched and contribute to exit 1.

### Surgical writers
- **Python (`sync/write_py.py`):** splice only `doc_span` (replace) or insert before `body[0]`
  (insert, when `doc_span is None`) at `body_col` indent; render from `normalize_prose`; always emit
  `"""`; escape `\`, embedded `"""`, trailing `"`. No-op short-circuit on `prose_equal`. Refuse
  raw/byte-prefixed docstrings (skip + report, never corrupt). Multiple edits per file applied
  bottom-to-top (descending start line) so spans stay valid. "Rest byte-identical" holds because
  every untouched line is the original list element.
- **Markdown (`sync/write_md.py`):** reuse `is_prose_line` (factored from `markdown._extract_prose`)
  as the single prose/meta boundary authority; replace only the **leading prose block** of the
  entity body (heading+blank → first `|`/`>`/`<!--` line), preserving table/fence/note and blank
  structure. No-op short-circuit on `prose_equal`. Refuse interleaved prose-after-meta (not v1).
  Multi-entity edits bottom-to-top.

### Module layout (`src/lg2m/sync/`, framework-free)
`__init__.py` (exports `run_sync`, `SyncResult`), `normalize.py` (leaf, stdlib only), `lockfile.py`
(stdlib `json`), `merge.py` (pure), `write_py.py`, `write_md.py`, `engine.py` (orchestration).
`diff/engine.py` imports `sync.normalize` (leaf, no cycle).

### Documented limitations (v1)
Raw/byte-prefixed docstrings unsupported (skip + exit 1). Prose must be the leading block of an
entity body (interleaved prose-after-meta refused, not guessed). Hash-only baseline (defer
`base_text` 3-way per `docs/prose-sync.md`).
