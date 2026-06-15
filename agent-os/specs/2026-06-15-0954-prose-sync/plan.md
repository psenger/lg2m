# lg2m Layer 6 — `lg2m sync`: prose write-back with a `.lg2m.lock` baseline

## Context

lg2m is green through layer 5 (193 tests, ~96% cov, ruff clean): `check` reconciles
topology / annotations / Markdown and **reports** `PROSE_DRIFT` read-only; `gen --from-doc`
/ `--from-code` are one-shot prose generators. The missing piece (PLAN Section 12, design of
record `docs/prose-sync.md`, roadmap "Future") is **`lg2m sync`**: a *write-only* verb that
reconciles the **free-prose slice** of each node/predicate between the Markdown `### entity`
paragraph and the function docstring, using a per-entity baseline so the two-way sync is safe.

This is the **first lg2m verb that mutates user `.py` source**, so the work is dominated by two
risky subsystems (a per-entity 3-way merge keyed off `.lg2m.lock`, and two surgical writers) plus
a foundational gap that exploration uncovered: **the code side captures no docstrings today**
(`annotations/reader.py` stops at the decorator line), so `Node.docstring` / `Predicate.docstring`
are always `None` and `check`'s `_check_prose` never actually fires. That capture sub-layer must
land first.

Intended outcome: `lg2m sync` makes docstrings and Markdown prose converge incrementally and
safely; `check` stays read-only and stops reporting `PROSE_DRIFT` once a `sync` reconciles it.

### Settled decisions (from shaping)
- **Scope:** sync covers **nodes + predicates only**; edges stay Markdown-only (no docstring home).
  Only the free-prose slice crosses the boundary — tables / `<!-- lg2m -->` fences / `> Note:` never
  enter a docstring.
- **Baseline:** a committed repo-root `.lg2m.lock` (JSON, stdlib only) of per-entity `base_hash`
  (sha256 of last-synced *normalized* prose), keyed graph → kind → id. Per-entity value is an object
  so a future `base_text` (true 3-way) can be added without a format break.
- **4-case engine + bootstrap (directional adopt):**
  - base present: md-only-changed → write docstring; code-only-changed → write Markdown;
    both-changed → conflict; neither → no-op.
  - **no base + one side empty, other has prose → adopt the non-empty side into the empty side**
    (the incremental form of `gen --from-doc`/`--from-code`); both present & equal → adopt silently;
    both present & unequal → conflict.
- **Conflict policy:** refuse + show diff by default; `--prefer code|doc` resolves; exit 1 on any
  unresolved conflict.
- **Doc write mechanism:** **targeted source-span edit** (stdlib only) — replace only the docstring
  node's line span, re-indent to the function body, leave the rest of the file byte-identical. No
  `ast.unparse` round-trip.
- **Framework-free invariant (stronger than `check`):** `sync` imports **no** framework even at
  runtime — prose lives in source text + Markdown, neither needs a compiled graph. The AST reader
  still never imports the target module. Make this an explicit invariant for `sync/`.

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
- First verb to mutate user `.py` source (high blast radius); surgical docstring write-back is a new mechanism.
- Foundational sub-layer required first: docstring capture across `annotations/reader.py` → `pipeline.py` → `diff/assemble.py` (confirmed missing; it's why `PROSE_DRIFT` never fires).
- Three new subsystems with no precedent: `.lg2m.lock` baseline store, per-entity 4-case merge, two surgical writers.
- New shared prose-normalization (dedent / newline / trailing-blank) reused by `engine._check_prose` and `sync`.
- New `cli.py sync` command + large test surface (4 cases, idempotency, byte-preservation, CliRunner exit codes, e2e on a copy of `examples/support_pipeline/`).
- Touches 5 existing source files + a new `sync/` package + new tests; ~1–3 days.

**Model Recommendation:** Opus
**Reason:** a cross-cutting, first-of-its-kind source-mutating verb layered on new merge/lockfile/writer subsystems.

**Session-split guidance (4/5 boundary):** Phase 1 (capture) and Phases 2–3 (lockfile + merge) are low-risk and self-contained; isolate Phase 4 (surgical writers) and Phases 5–6 to their own focused session if context runs hot.

---

## Quality gates

Per-task **Done-when** only (concrete commands/checks). No separate Acceptance-Criteria section.
`--no-cov` is used for focused single-file runs; the final task enforces the 90% gate.

---

## Task 1: Save Spec Documentation

- [x] Create `agent-os/specs/2026-06-15-0954-prose-sync/` with `plan.md` (this plan), `shape.md`, `standards.md`, `references.md`, and an empty `visuals/`.
  - `shape.md` = the **Context** + **Settled decisions** above, plus the **Key design reference** section below (normalize order, lock schema, module layout, writer algorithms, the directional-adopt table, the documented limitations).
  - `standards.md` = full content of: `testing/testing`, `testing/mocking`, `global/tdd-workflow`, `global/coding-conventions`, `global/clean-code`, `global/simplicity`, `global/value-objects`, `patterns/guards`, `error-handling/error-handling`, `ir/identity`, `ir/mutability` (read each from `agent-os/standards/` and paste).
  - `references.md` = the reuse map in **Critical Files / reuse** below, plus pointers to prior specs `2026-06-14-2225-cli-typer` and `2026-06-14-2301-scaffold-gen`, design of record `docs/prose-sync.md`, and PLAN Section 12 / 14.

---

## Task 2: **Phase 1 — Docstring capture + make `PROSE_DRIFT` real (nodes + predicates)**

- [x] **Task 2.1: Capture docstrings + spans in the AST reader**
  - [x] Extend `AnnoRef` (`annotations/reader.py`) with `docstring: str | None`, `doc_span: tuple[int,int] | None` (1-based inclusive), `body_col: int | None`.
  - [x] For node/predicate decorators, from the decorated `FunctionDef`/`AsyncFunctionDef`: `ast.get_docstring(fn, clean=False)`; if `fn.body[0]` is an `ast.Expr` wrapping a `str` `ast.Constant`, set `doc_span = (expr.lineno, expr.end_lineno)`; always set `body_col = fn.body[0].col_offset`. Stay `ast`-only — never import the target.

  ### Done when
  - [x] `tests/test_reader.py` cases assert capture for: multi-line docstring (span spans >1 line), single-line docstring (`start==end`), and no docstring (`doc_span is None`, `body_col` set).
  - [x] `./.venv/bin/python -m pytest tests/test_reader.py --no-cov -q` green; `./.venv/bin/ruff check src tests` clean.

- [x] **Task 2.2: Thread docstring text to the code-side IR**
  - [x] `pipeline.gather_annotations` records `ref.docstring` on `NodeEntry`/`PredicateEntry` (registry-carried, `compare=False`; no return-signature change, so no call-site churn).
  - [x] `diff/assemble.assemble_code_model` sets `Node.docstring` / `Predicate.docstring` from those registry entries (replacing the always-`None` pass-through). No caller change needed.

  ### Done when
  - [x] `tests/test_assemble.py` asserts a code-side model carries node **and** predicate docstrings.
  - [x] `./.venv/bin/python -m pytest tests/test_assemble.py --no-cov -q` green.

- [x] **Task 2.3: Normalization helper + make `_check_prose` real for nodes and predicates**
  - [x] Add `src/lg2m/sync/normalize.py`: `normalize_prose(text) -> str`, `prose_hash(text) -> str` (sha256 hex), `prose_equal(a,b) -> bool`. Canonical order: CRLF→LF; dedent (`inspect.cleandoc`, which also strips the first line so a flush-left docstring first line dedents correctly); per-line `rstrip`; collapse blank-line runs to one; final `strip`.
  - [x] In `diff/engine._check_prose`: switch the comparison to `not prose_equal(...)` **and** extend it to predicates (`code.predicates.keys() & doc.predicates.keys()`).

  ### Done when
  - [x] `tests/test_normalize.py` asserts indented-docstring vs column-0-markdown normalize equal; CRLF/trailing-blank idempotence.
  - [x] `tests/test_engine.py` keeps `PROSE_DRIFT` WARNING/report-only and adds a predicate `PROSE_DRIFT` case + a normalization-equivalence (no-drift) case.
  - [x] `./.venv/bin/python -m pytest tests/test_engine.py tests/test_normalize.py --no-cov -q` green. (Also: full `not langgraph` subset 186 passed — no ripple.)

---

## Task 3: **Phase 2 — `.lg2m.lock` store**

- [x] **Task 3.1: Lockfile read/write**
  - [x] `src/lg2m/sync/lockfile.py`: `Lock` (thin dataclass over the dict), `load_lock(path) -> Lock` (empty when absent), `write_lock(path, lock)` via `json.dumps(obj, indent=2, sort_keys=True) + "\n"`, `base_hash(lock, gid, kind, key) -> str|None`, `set_base(lock, gid, kind, key, h)`. Schema: `{"version":1,"graphs":{<gid>:{"nodes":{<id>:{"base_hash":...}},"predicates":{...}}}}`.

  ### Done when
  - [x] `tests/test_lockfile.py` asserts: missing file → empty lock; write→load round-trip; byte-stable re-serialization (deterministic key order); `set_base`/`base_hash` round-trip.
  - [x] `./.venv/bin/python -m pytest tests/test_lockfile.py --no-cov -q` green.

---

## Task 4: **Phase 3 — Pure merge decision table**

- [x] **Task 4.1: `merge.py` decision function**
  - [x] `src/lg2m/sync/merge.py`: pure `decide(base_hash, code_prose, md_prose, prefer) -> Action` where `Action ∈ {WRITE_CODE, WRITE_MD, ADOPT, NOOP, CONFLICT}`. (Tightened from the planned set: directional adopt is operationally a write, so it reuses WRITE_CODE/WRITE_MD instead of ADOPT_CODE/ADOPT_MD; SKIP_RAW_PREFIX moved to the writer in Task 5.1, since `decide` only sees prose strings, not source.) Implements the base-present 4 cases **and** the no-base directional-adopt rule. `--prefer code` → WRITE_MD; `--prefer doc` → WRITE_CODE.

  ### Done when
  - [x] `tests/test_merge.py` covers all rows of the table (base-present ×4, no-base ×3) plus both `--prefer` resolutions.
  - [x] `./.venv/bin/python -m pytest tests/test_merge.py --no-cov -q` green.

---

## Task 5: **Phase 4 — Surgical writers (framework-free, unit-tested)**

- [x] **Task 5.1: Python docstring write-back (`sync/write_py.py`)**
  - [x] `write_docstring(source, ref, new_prose) -> WriteResult`: split into lines, splice only `doc_span` (replace) or insert before `body[0]` (when `doc_span is None`, using new `ref.body_lineno`) at `body_col` indent; render via `_render_docstring` from `normalize_prose`; always emit `"""`; `_escape` backslashes / embedded `"""` / trailing `"`.
  - [x] No-op short-circuit when `prose_equal(ref.docstring, new_prose)`. **Refuse** (`WriteResult.skipped_raw_prefix=True`, source unchanged) if the original docstring line carries a raw/byte prefix. (Engine applies multiple edits per file bottom-to-top — Task 6.1.)

  ### Done when
  - [x] `tests/test_write_py.py` asserts: insert into a no-docstring function (the common case), replace a multi-line docstring, single-line docstring replace, idempotent re-write is byte-identical, lines outside the span unchanged, raw-prefix refused.
  - [x] `./.venv/bin/python -m pytest tests/test_write_py.py --no-cov -q` green.

- [x] **Task 5.2: Markdown prose-span write-back (`sync/write_md.py`)**
  - [x] Factor `is_prose_line` out of `parsing/markdown._extract_prose` and export it (single authority for the prose/meta boundary); import it in `write_md.py`.
  - [x] `write_prose(md_lines, entity, new_prose) -> MdWriteResult`: replace only the **leading prose block** of the entity body, preserving table/fence/note + blank structure; no-op short-circuit on `prose_equal`; **refuse** if prose appears after meta (interleaved shape, not in v1). (Engine applies multi-entity edits bottom-to-top — Task 6.1.)

  ### Done when
  - [x] `tests/test_write_md.py` asserts: a node followed by a `<!-- lg2m -->` fence keeps the fence; a node with a `> Note:` keeps it; `parse_markdown` round-trips the result; idempotent re-write byte-identical.
  - [x] `tests/test_markdown.py` still green (refactor changed nothing observable).
  - [x] `./.venv/bin/python -m pytest tests/test_write_md.py tests/test_markdown.py --no-cov -q` green.

---

## Task 6: **Phase 5 — Sync engine (framework-free)**

- [x] **Task 6.1: `sync/engine.py::run_sync`**
  - [x] `run_sync(config_path, graph_id, *, prefer, dry_run, lock_path) -> SyncResult`: resolve config → markdown path + package source dir (path resolution via new `_find_package_dir`, **no import**); `parse_markdown` the doc; `reader.read_file` over package `*.py` for code prose + spans; for each node/predicate run `merge.decide`; apply writers grouped per file bottom-to-top (skip writes under `dry_run`); rewrite `.lg2m.lock` only when its serialized content changes. `SyncResult` carries code/md writes, adopts, conflicts, raw-prefix + interleaved skips, `exit_code`, `wrote_files`.

  ### Done when
  - [x] `tests/test_sync_engine.py` (fixture source dir + markdown in `tmp_path`) asserts each of the four cases converges and the lock updates; conflict path writes nothing and is reported; `dry_run` writes nothing.
  - [x] `./.venv/bin/python -m pytest tests/test_sync_engine.py --no-cov -q` green (no `@pytest.mark.langgraph` needed).

---

## Task 7: **Phase 6 — CLI command + end-to-end**

- [x] **Task 7.1: `sync` command in `cli.py`**
  - [x] Add `@app.command() def sync(...)` mirroring `gen`: `graph_id` (`_GRAPH_ID_ARG`), `--config` (`_CONFIG_OPT`), `--prefer` (new `Prefer` enum, default none), `--dry-run`, `--lock` (default repo-root `.lg2m.lock`). Module-level `typer.Option` constants (B008). Reuse `_resolve_config` / `_load_graphs` / `_resolve_graph_id` / `_fail`. Exit: `0` synced-or-clean, `1` unresolved conflict, `2` usage/config.

  ### Done when
  - [x] `tests/test_cli_sync.py` via `CliRunner`: `--dry-run` writes nothing, exit 0; unresolved conflict exit 1; bad config exit 2 (mirrors `tests/test_cli_gen.py`).
  - [x] `./.venv/bin/python -m pytest tests/test_cli_sync.py --no-cov -q` green.

- [x] **Task 7.2: End-to-end on a copy of `examples/support_pipeline/`**
  - [x] `tests/test_sync_e2e.py`: copy the example into `tmp_path`; drift one node's md prose → `sync` → assert the docstring matches (normalized); drift one predicate's docstring → `sync` → assert md updated; `sync` again → no writes, `.lg2m.lock` byte-stable; assert `_check_prose` reports **no** `PROSE_DRIFT` after.

  ### Done when
  - [x] `tests/test_sync_e2e.py` green.
  - [x] Full `./.venv/bin/python -m pytest -q` passes the 90% coverage gate; `./.venv/bin/ruff check src tests` clean.

---

## Critical Files / reuse

**New (`src/lg2m/sync/`):** `__init__.py` (exports `run_sync`, `SyncResult`), `normalize.py`, `lockfile.py`, `merge.py`, `write_py.py`, `write_md.py`, `engine.py`.

**Edited:**
- `src/lg2m/annotations/reader.py` — extend `AnnoRef` (docstring + span + body_col); capture in the decorator classifier. Keep import-free.
- `src/lg2m/pipeline.py` — `gather_annotations` returns the extra `prose` map.
- `src/lg2m/diff/assemble.py` — `assemble_code_model` sets `Node`/`Predicate` docstrings from the map.
- `src/lg2m/diff/engine.py` — `_check_prose` uses `prose_equal` and covers predicates.
- `src/lg2m/parsing/markdown.py` — export `is_prose_line` (factored from `_extract_prose`).
- `src/lg2m/cli.py` — new `sync` command + option constants.

**Reused unchanged:** `cli.py` helpers `_resolve_config` / `_load_graphs` / `_resolve_graph_id` / `_fail`; `parsing/markdown.parse_markdown` + `Entity(start,end,lines,prose)`; `annotations/reader.read_file`; `diff/categories.DriftCategory.PROSE_DRIFT`; `ir.Node`/`Predicate` (`prose`/`docstring` already present, `compare=False`).

**Documented limitations (v1):** raw/byte-prefixed docstrings are unsupported (skip + exit 1, never corrupt); prose must be the leading block of an entity body (interleaved prose-after-meta is refused, not guessed); hash-only baseline (defer `base_text` 3-way).

---

## Verification

- Per-phase: the `### Done when` commands above (focused `--no-cov` runs + `ruff check src tests`).
- Full gate: `./.venv/bin/python -m pytest -q` (incl. `@langgraph`, 90% cov) and `./.venv/bin/python -m pytest -m "not langgraph" -q` (framework-free subset) both green; `./.venv/bin/ruff check src tests` clean.
- Behavioral spine (Task 7.2): the four merge cases converge; `sync` twice is a no-op with a byte-stable `.lg2m.lock`; `check` writes nothing and stops reporting `PROSE_DRIFT` after a `sync`; a docstring edit changes only the docstring span and a Markdown edit only the entity prose span.
