# Introspect + Diff + Report — lg2m layer 2b (plan)

**Spec folder:** `agent-os/specs/2026-06-14-2130-introspect-diff-report/`

## Context

Layers 1 (IR + parsers) and 2a (annotations + router) are green. This layer builds the
framework-free reconciliation core: a Fake topology + the annotation registry + the layer-1
Markdown IR, reconciled into a `DriftReport`. See `shape.md` for scope, decisions, the canonical
oracle sets, and acceptance criteria. The full design narrative is the approved implementation
plan at `~/.claude/plans/continue-lg2m-layer-2b-idempotent-cake.md`.

## Standards applied

The authority is the full text under `agent-os/standards/`; these are the ones this layer is
written against:

- `@agent-os/standards/patterns/adapter.md` — the `GraphIntrospector` port + Fake/real adapters.
- `@agent-os/standards/patterns/strategy.md` — the per-category checks as a list of uniform functions.
- `@agent-os/standards/global/hexagonal-architecture.md` — IR is the domain currency; adapters
  translate third-party shape, the core (`reconcile`) never sees a framework type.
- `@agent-os/standards/global/value-objects.md` — `DriftItem`/`DriftReport` and the canonical IR.
- `@agent-os/standards/error-handling/error-handling.md`, `@agent-os/standards/patterns/guards.md`
  — total recovery (skip non-derivable meta, never crash) and severity classification.
- `@agent-os/standards/testing/{testing,mocking}.md` — the Fake double + the clean-oracle gate.
- Carried over: `@agent-os/standards/global/{simplicity,clean-code,coding-conventions}.md`.

## Build order (each phase ends green + ruff-clean)

1. **introspect base + Fake** — `introspect/{base,__init__}.py`. ✅
2. **categories + report model** — `diff/categories.py`, `report/model.py`. ✅
3. **assemble doc side + `canonicalize`** — `diff/assemble.py` (fork/join collapse, composite
   flatten, `[*]` → sentinels, Edges-table kind authority). ✅
4. **assemble code side + oracle Fake** — `assemble_code_model` (+ subgraph-suffix anno match) and
   the test `oracle_topology()` / `load_oracle_registry()`. ✅
5. **engine: `reconcile` + 7 checks + `_fold_diagnostics`** — `diff/engine.py`. ✅
6. **report renderers** — `report/{text,json}.py`. ✅

## Critical files

- New: `src/lg2m/introspect/{__init__,base}.py`, `src/lg2m/diff/{__init__,categories,assemble,engine}.py`,
  `src/lg2m/report/{__init__,model,text,json}.py`.
- New tests: `tests/test_{introspect,diff_categories,assemble,engine,report}.py`, plus the
  non-collected helper `tests/_oracle.py`.
- Edited: `tests/conftest.py` (golden source-dir fixture).
- Consumed unchanged: `ir.py`, `annotations/{registry,reader}.py`, `parsing/*`.

## Verification

```bash
source .venv/bin/activate
python -m pytest -q                  # full suite green; 90% coverage gate holds (~96%)
ruff check src tests                 # clean (examples/ intentionally not linted)
python -c "import sys, lg2m; import lg2m.introspect, lg2m.diff.engine, lg2m.report; \
  assert 'langgraph' not in sys.modules"
```

## Status

All six phases complete and green: **122 tests, ~96% coverage, ruff clean, framework-free.**
The clean oracle reconciles to an empty `DriftReport`.
