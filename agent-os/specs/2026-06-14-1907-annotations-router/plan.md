# Annotations + Router — lg2m layer 2a

**Spec folder (created by Task 1):** `agent-os/specs/2026-06-14-1907-annotations-router/`

## Context

`lg2m` layer 1 (the framework-free IR + Markdown/`stateDiagram-v2` parsers) is
complete and green (51 tests). This spec implements **layer 2a: the authoring
annotations and the Model-A router** — `docs/design.md` build-order step 2, sliced to the
annotation surface only. In scope: `annotations/{decorators,registry,router,reader}.py`
and the `__init__.py` exports. Out of scope (later slices): `introspect/*`,
`diff/*`, `report/*`, `cli.py`, and the router's `.as_runnable_branch()` LangChain
emit. **No `langgraph` / `langchain_core` import appears anywhere in lg2m code or
its tests.**

Why this scope: the generated router is the spine of the whole design
(`docs/design.md` Section 3). The diagram labels, the runtime selector, and the
`add_conditional_edges` `path_map` are all produced from **one** ordered
`[(predicate, target), …, (ELSE, target)]` mapping, so they cannot drift. The
decorators are metadata-only (they record into a per-import registry and return
the target unchanged); the reader is a pure-`ast` pass that recovers the same
mapping and `file:line` from source text without importing it. Cutting the spec
here makes it fully testable against a concrete oracle — the already-authored
`examples/support_pipeline/src/support_pipeline/{routing,predicates,state,nodes}.py` —
and unblocks the introspection + diff slice.

The four annotation modules are new. `ir.py` and `__init__.py` get small,
justified edits (the `ELSE_LABEL` hoist and the export fill-in).

## Execution Protocol (MANDATORY)

These rules govern any agent executing this plan. They are not optional.

1. **The checkbox is the source of truth.** A task is not complete until its checkbox in this file has been changed from `- [ ]` to `- [x]` using the Edit tool. Verbal claims of completion in chat are not completion.
2. **Flip immediately.** After finishing any action, edit this file to update the checkbox **before** beginning the next action. Do not batch checkbox updates across multiple tasks.
3. **Done-when gates are blocking.** If a task has a `### Done when` block, every item in it must be verifiably true before that task's checkbox may be flipped to `[x]`. No exceptions.
4. **Failure stops the run.** If any Done-when item cannot be satisfied, stop. Do not proceed to later tasks. Report the failure and wait for direction.
5. **No silent skips.** If a task is intentionally skipped, change `- [ ]` to `- [~]` and append a one-line note explaining why. Never delete a task.
6. **Self-audit before reporting completion.** Before telling the user the plan is done, re-read this file and confirm every checkbox is `[x]` or `[~]`. If any `[ ]` remains, the plan is not complete.

Violating these rules is a defect. Treat them as you would treat a failing test.

## Complexity

**Rating:** 4 — Complex

**Evidence:**
- **The generated router is the novel spine:** `annotations/router.py` produces a `path_fn` whose behavior equals first-match-then-`[else]`, returns the matched predicate **name**, owns a `path_map` keyed by predicate name, **lazily** resolves predicate names to `@predicate` functions from the registry (`routing.py` does not import `predicates.py`), and rejects missing/duplicate `ELSE` and a predicate literally named `[else]`.
- **Dual decorator forms:** `@node("id")`/`@predicate("name")` are parametrized; `@state_model`/`@data_model` are bare class decorators; all feed a resettable per-import registry.
- **A second parsing surface:** `reader.py` is a pure-`ast` recovery of the router mapping and `file:line` from source text, distinct from layer 1's line parsers.
- **Bounded oracle (why 4, not 5):** the example's `routing/predicates/state/nodes.py` give exact target usage to test against.

**Model Recommendation:** Opus — the router generation and AST recovery reward careful edge-case reasoning.
**Context note:** if context tightens, **Phase 3 (the AST reader)** is the natural split point.

## Standards

Apply these (selected in `/inject-standards`; full text copied into `standards.md` by Task 1):

### Annotations & router (the Model-A spine)
@agent-os/standards/patterns/decorator.md
@agent-os/standards/patterns/factory.md

### Introspection seam (forward constraint: stay framework-free)
@agent-os/standards/patterns/adapter.md
@agent-os/standards/patterns/strategy.md
@agent-os/standards/global/hexagonal-architecture.md
@agent-os/standards/global/coupling-cohesion.md

### Diff & diagnostics (forward constraint for validation shape)
@agent-os/standards/error-handling/error-handling.md
@agent-os/standards/patterns/error-first.md
@agent-os/standards/patterns/guards.md
@agent-os/standards/global/value-objects.md

### Testing with fakes
@agent-os/standards/testing/mocking.md
@agent-os/standards/testing/testing.md

### Carried over from layer 1
@agent-os/standards/global/simplicity.md
@agent-os/standards/global/clean-code.md
@agent-os/standards/global/coding-conventions.md

## Key design decisions

1. **`ELSE_LABEL` has one home.** `parsing/mermaid.py` currently owns
   `ELSE_LABEL = "[else]"`. The router's `path_map` default key, the IR `Route`
   default, the predicate guard, and the reader's recovered ELSE must all use
   that exact literal, so it is **hoisted to `ir.py`** and `mermaid.py` +
   `annotations/*` import it from there. This is the DRY single-source for the
   reserved label and the only reason a label check can hold "by construction".
2. **Missing predicate at call time raises `LookupError`** (naming the source and
   the predicate). Swallowing a runtime miss into `[else]` would hide drift; the
   non-fatal, static signal is the later diff layer's `PREDICATE_UNDEFINED`
   diagnostic, not this layer's concern.
3. **The reader stays single-responsibility:** it recovers `AnnoRef`/`RouterRef`
   values plus a thin `merge_locations(result, registry)` that attaches
   `SourceLocation` by id/name/source. Graph assembly belongs to the diff layer.
4. **Annotation location = the decorator line** (e.g. the `@node("ingest_ticket")`
   line), recovered from `decorator_list[i].lineno`, since that is where the lg2m
   annotation lives and what `check` should point at.

## Acceptance Criteria

Stable ids; `### Done when` blocks reference them. All counts/lines are read from
the real example files under `examples/support_pipeline/src/support_pipeline/`.

- **AC-01 (node decorator).** Given `@node("ingest_ticket")` on a function, When the module imports, Then `registry.nodes["ingest_ticket"].target` is that function and the function is returned unchanged (still callable).
- **AC-02 (predicate decorator).** Given `@predicate("should_escalate")` on a function, When imported, Then `registry.predicates["should_escalate"].target` is that function, returned unchanged.
- **AC-03 (data_model bare).** Given `@data_model` on `class Ticket`, When imported, Then `registry.models["Ticket"]` exists with `is_graph_state is False`, class returned unchanged.
- **AC-04 (state_model bare).** Given `@state_model` on `class PipelineState`, When imported, Then `registry.models["PipelineState"].is_graph_state is True`.
- **AC-05 (path_map).** Given `lg2m.router("classify_intent", [("should_escalate","escalate_to_human"),("should_auto_resolve","auto_resolve"),(lg2m.ELSE,"investigate")])`, Then `router.path_map == {"should_escalate":"escalate_to_human","should_auto_resolve":"auto_resolve","[else]":"investigate"}` and `router.source`/`router.branches`/`router.else_target` match.
- **AC-06 (returns the name).** Given that router and a registered `@predicate("should_escalate")` that is truthy for the test state, When the path_fn is called, Then it returns the string `"should_escalate"` (the name, not the target).
- **AC-07 (else).** Given the same router, When every predicate is falsy, Then the path_fn returns `"[else]"`.
- **AC-08 (first-match order).** Given `should_escalate` falsy and `should_auto_resolve` truthy, Then the path_fn returns `"should_auto_resolve"` (ordered scan; the else default is never scanned regardless of its position in the list).
- **AC-09 (missing else).** Given branches with no `ELSE`, Then `lg2m.router(...)` raises `ValueError` about the missing default.
- **AC-10 (reserved label as predicate target key).** Given a branch keyed by the string `"[else]"` (not the sentinel), Then construction raises `ValueError` rejecting the reserved label.
- **AC-11 (duplicate else).** Given two `ELSE` elements, Then construction raises `ValueError` ("more than one ELSE").
- **AC-12 (predicate named else).** Given `@predicate("[else]")`, Then the decorator raises `ValueError`.
- **AC-13 (two predicates, one target).** Given branches `("a","compose_reply")` and `("b","compose_reply")`, Then `path_map` has two distinct keys both mapping to `"compose_reply"` (two labelled edges).
- **AC-14 (undefined predicate at call).** Given a router referencing `"should_escalate"` with no such `@predicate` registered, When the path_fn is called, Then it raises `LookupError` naming the source and the missing predicate.
- **AC-15 (reader recovers the route).** Given the reader parses `routing.py` **as text** (no import), Then it recovers `Route(source_id="classify_intent", branches=(("should_escalate","escalate_to_human"),("should_auto_resolve","auto_resolve")), else_target="investigate")` with `loc.file` = that path and `loc.line == 33`.
- **AC-16 (reader recovers predicates).** Given the reader parses `predicates.py`, Then it recovers predicate `AnnoRef`s for `should_escalate` (decorator line 20) and `should_auto_resolve` (line 26).
- **AC-17 (reader recovers models).** Given the reader parses `state.py`, Then it recovers `("data_model","Ticket", line 41)` and `("state_model","PipelineState", line 51)`, distinguishing the two bare decorators by kind.
- **AC-18 (reader recovers nodes).** Given the reader parses `nodes.py`, Then it recovers exactly **12** node `AnnoRef`s with ids `{ingest_ticket, fetch_history, lookup_account, classify_intent, auto_resolve, escalate_to_human, map_items, process_item, reduce_items, compose_reply, gather_logs, analyze}` (representative decorator lines: `ingest_ticket`@23, `analyze`@130); `investigate` is **not** among them (it is the subgraph, carries no `@node`); and parsing does **not** import `nodes.py` (so `langgraph` is not imported).
- **AC-19 (ELSE both spellings).** Given a file using `from lg2m import ELSE` and a bare `ELSE` in the branches, Then the reader recovers the same `else_target` as the `lg2m.ELSE` attribute form.
- **AC-20 (public exports, no framework import).** Given `import lg2m`, Then `lg2m.node`, `lg2m.predicate`, `lg2m.router`, `lg2m.ELSE`, `lg2m.state_model`, `lg2m.data_model` are all present, and `"langgraph" not in sys.modules` as a result of importing lg2m.

## Tasks

> Gate style: **Done-when + Acceptance criteria.** Each `### Done when` lists concrete checks; where an AC applies it is named. Each subtask is independently completable in under 2 hours. `pytest` from the repo root via `./.venv/bin/python -m pytest`; `./.venv/bin/ruff check src tests` stays clean throughout. (The layer-1 `.venv` with pytest + ruff already exists.)

## Task 1: Save Spec Documentation

- [x] Create `agent-os/specs/2026-06-14-1907-annotations-router/` containing:
  - `plan.md` — this plan.
  - `shape.md` — scope, decisions, and AC-01..AC-20 verbatim.
  - `standards.md` — full text of each standard under `## Standards`.
  - `references.md` — the example annotation files (the oracle) and `docs/design.md` Sections 3/4/14.
  - `visuals/` — empty (none).

### Done when
- [x] All five entries exist and `plan.md`/`shape.md`/`standards.md`/`references.md` are non-empty.
- [x] `shape.md` contains AC-01 through AC-20.

- [x] **Phase 1: decorators + registry + exports**

  - [x] **Task 1.1: hoist `ELSE_LABEL` to `ir.py`**
    - [x] Add `ELSE_LABEL = "[else]"` to `src/lg2m/ir.py`; change `parsing/mermaid.py` to `from lg2m.ir import ELSE_LABEL` (keep the name resolvable as `mermaid.ELSE_LABEL`).

    ### Done when
    - [x] `from lg2m.ir import ELSE_LABEL` works and `ELSE_LABEL == "[else]"`.
    - [x] The full layer-1 suite stays green (`pytest tests/ -q`) and ruff is clean.

  - [x] **Task 1.2: `annotations/__init__.py` + `registry.py`**
    - [x] Empty `annotations/__init__.py`; `registry.py` per **Appendix A** (`NodeEntry`/`PredicateEntry`/`ModelEntry`/`RouterEntry` frozen entries, mutable `Registry`, `get_registry()`, `reset()`).
    - [x] `tests/test_registry.py` (reset round-trip).

    ### Done when
    - [x] `pytest tests/test_registry.py` green; `ruff check src/lg2m/annotations/registry.py` clean.

  - [x] **Task 1.3: `annotations/decorators.py`**
    - [x] `node`/`predicate` (parametrized), `state_model`/`data_model` (bare) per **Appendix B**; guards reject empty ids/names and a predicate named `[else]`; every decorator returns its target unchanged.
    - [x] `tests/test_decorators.py` (AC-01..AC-04, AC-12, "returns unchanged").

    ### Done when
    - [x] AC-01, AC-02, AC-03, AC-04, AC-12 satisfied; `pytest tests/test_decorators.py` green; ruff clean.

  - [x] **Task 1.4: fill `src/lg2m/__init__.py` exports**
    - [x] Add `node, predicate, router, ELSE, state_model, data_model` to the imports and `__all__` (keep the IR re-exports).
    - [x] `tests/test_init_exports.py` asserting AC-20 (presence + `"langgraph" not in sys.modules`).

    ### Done when
    - [x] AC-20 satisfied; ruff clean.

  - [x] **Task 1.5: autouse `reset_registry` fixture**
    - [x] Add an autouse fixture to `tests/conftest.py` calling `lg2m.annotations.registry.reset()` in teardown; a cross-test isolation test proves registrations do not leak.

    ### Done when
    - [x] Two tests registering the same id in sequence do not interfere; full suite green; ruff clean.

- [x] **Phase 2: router (path_fn + path_map + validation)**

  - [x] **Task 2.1: `ELSE` sentinel + `Router` class**
    - [x] `Router` per **Appendix C**: `path_map` keyed by predicate name (`ELSE_LABEL` reserved); `__call__` lazily resolves `@predicate` functions from the registry, first-match returns the name, else returns `ELSE_LABEL`; exposes `source`/`branches`/`else_target`/`path_map`.

    ### Done when
    - [x] AC-05, AC-06, AC-07, AC-08, AC-13 satisfied; ruff clean.

  - [x] **Task 2.2: `router()` factory + `_validate_branches` guards**
    - [x] Validate exactly one `ELSE`, reject `"[else]"` as a predicate name, reject missing `ELSE`, require ≥1 predicate branch, non-empty string names/targets; register a `RouterEntry`.

    ### Done when
    - [x] AC-09, AC-10, AC-11 satisfied (each `ValueError` asserted with `pytest.raises(match=...)`); a test confirms `registry.routers["classify_intent"].path_fn` is the returned router; ruff clean.

  - [x] **Task 2.3: lazy-resolution error path + framework-free check**
    - [x] Missing predicate at call time raises `LookupError`; confirm no `langgraph`/`langchain` import in `router.py` (the `.as_runnable_branch()` hook is a docstring note only).

    ### Done when
    - [x] AC-14 satisfied; `grep` shows no framework import in `router.py`; `pytest tests/test_router.py` green; ruff clean.

- [x] **Phase 3: reader (AST recovery + merge)**

  - [x] **Task 3.1: decorator recovery**
    - [x] `read_file(path)` parses with `ast`; recover the four decorators (bare vs parametrized) with the **decorator line**, per **Appendix D**.

    ### Done when
    - [x] AC-16, AC-17, AC-18 satisfied against the real example files (parsed as text; no import side effect).

  - [x] **Task 3.2: `lg2m.router(...)` recovery**
    - [x] Recover source + ordered branches + ELSE (`lg2m.ELSE` attribute and bare `ELSE` name) into an `ir.Route` with `loc`; skip non-literal elements rather than crash.

    ### Done when
    - [x] AC-15, AC-19 satisfied.

  - [x] **Task 3.3: `merge_locations` + full-suite gate**
    - [x] Thin `merge_locations(result, registry)` keyed by id/name/source attaching `SourceLocation`; the reader call itself imports nothing.

    ### Done when
    - [x] `pytest tests/ -q` all green; `ruff check src tests` clean; no test leaves files in the working tree.

## Critical Files

New (this layer): `src/lg2m/annotations/{__init__,registry,decorators,router,reader}.py`, plus `tests/test_{registry,decorators,init_exports,router,reader}.py`.
Edited (small): `src/lg2m/ir.py` (add `ELSE_LABEL`), `src/lg2m/parsing/mermaid.py` (import it), `src/lg2m/__init__.py` (exports), `tests/conftest.py` (reset fixture).
Oracle (read-only): `examples/support_pipeline/src/support_pipeline/{routing,predicates,state,nodes}.py`.
Design of record: `docs/design.md` Sections 3, 4, 14.

## Verification

From the repo root, framework-free:

1. `./.venv/bin/python -m pytest tests/ -q` — all green (layer-1 suite plus the new `test_{registry,decorators,init_exports,router,reader}.py`).
2. `./.venv/bin/python -c "import sys, lg2m; assert 'langgraph' not in sys.modules"` — importing lg2m drags in no framework.
3. `./.venv/bin/ruff check src tests` — clean.
4. Spot-check the spine: in a REPL, register two `@predicate`s and a `lg2m.router`, assert the path_fn returns the matched name and `path_map` is keyed by predicate name.

## Appendix A: `registry.py`

```python
"""Per-import registry that the lg2m annotations and router populate.

A mutable assembly buffer (compare ir.GraphModel): the decorators write into it
as the user's module imports; lg2m later reads it to build the IR. Module-level
singleton so decorators need no threading; reset() restores a clean buffer for
per-graph isolation and test independence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class NodeEntry:
    id: str
    target: Callable[..., Any]
    module: str | None
    lineno: int | None


@dataclass(frozen=True)
class PredicateEntry:
    name: str
    target: Callable[..., Any]
    module: str | None
    lineno: int | None


@dataclass(frozen=True)
class ModelEntry:
    name: str               # class __name__
    target: type
    is_graph_state: bool    # True for @state_model, False for @data_model
    module: str | None
    lineno: int | None


@dataclass(frozen=True)
class RouterEntry:
    source: str
    branches: tuple[tuple[str, str], ...]
    else_target: str
    path_fn: Callable[[Any], str]
    module: str | None
    lineno: int | None


@dataclass
class Registry:
    nodes: dict[str, NodeEntry] = field(default_factory=dict)
    predicates: dict[str, PredicateEntry] = field(default_factory=dict)
    models: dict[str, ModelEntry] = field(default_factory=dict)
    routers: dict[str, RouterEntry] = field(default_factory=dict)

    def reset(self) -> None:
        self.nodes.clear()
        self.predicates.clear()
        self.models.clear()
        self.routers.clear()


_REGISTRY = Registry()


def get_registry() -> Registry:
    return _REGISTRY


def reset() -> None:
    """Clear the shared registry. Call between graphs and in test teardown."""
    _REGISTRY.reset()
```

## Appendix B: `decorators.py`

```python
"""lg2m authoring decorators: metadata only, target returned unchanged.

Parametrized:  @node("id")   @predicate("name")
Bare:          @state_model   @data_model
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, TypeVar

from lg2m.ir import ELSE_LABEL
from lg2m.annotations.registry import ModelEntry, NodeEntry, PredicateEntry, get_registry

F = TypeVar("F", bound=Callable[..., Any])
C = TypeVar("C", bound=type)


def node(node_id: str) -> Callable[[F], F]:
    _require_nonempty(node_id, "node id")
    reg = get_registry()

    def decorate(fn: F) -> F:
        reg.nodes[node_id] = NodeEntry(node_id, fn, getattr(fn, "__module__", None),
                                       _func_lineno(fn))
        return fn

    return decorate


def predicate(name: str) -> Callable[[F], F]:
    _require_nonempty(name, "predicate name")
    if name == ELSE_LABEL:
        raise ValueError(f"predicate name cannot be the reserved label {ELSE_LABEL!r}")
    reg = get_registry()

    def decorate(fn: F) -> F:
        reg.predicates[name] = PredicateEntry(name, fn, getattr(fn, "__module__", None),
                                              _func_lineno(fn))
        return fn

    return decorate


def state_model(cls: C) -> C:
    return _record_model(cls, is_graph_state=True)


def data_model(cls: C) -> C:
    return _record_model(cls, is_graph_state=False)


def _record_model(cls: C, *, is_graph_state: bool) -> C:
    get_registry().models[cls.__name__] = ModelEntry(
        cls.__name__, cls, is_graph_state, getattr(cls, "__module__", None), _class_lineno(cls)
    )
    return cls


def _func_lineno(target: Callable[..., Any]) -> int | None:
    code = getattr(target, "__code__", None)
    return getattr(code, "co_firstlineno", None) if code is not None else None


def _class_lineno(cls: type) -> int | None:
    try:
        return inspect.getsourcelines(cls)[1]
    except (OSError, TypeError):
        return None


def _require_nonempty(value: Any, what: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty string, got {value!r}")
```

## Appendix C: `router.py`

```python
"""lg2m.router: the Model-A routing spine (a factory generating the path_fn).

The generated selector resolves predicate names to @predicate functions lazily
from the registry, evaluates them in order, and returns the NAME of the first
truthy predicate or the reserved "[else]" key. Deferred hook (LangChain layer,
NOT here): .as_runnable_branch().
"""

from __future__ import annotations

from typing import Any

from lg2m.ir import ELSE_LABEL
from lg2m.annotations.registry import RouterEntry, get_registry


class _Else:
    __slots__ = ()

    def __repr__(self) -> str:
        return "lg2m.ELSE"


ELSE = _Else()


class Router:
    def __init__(self, source: str, branches: tuple[tuple[str, str], ...],
                 else_target: str) -> None:
        self.source = source
        self.branches = branches
        self.else_target = else_target
        self.path_map: dict[str, str] = {name: target for name, target in branches}
        self.path_map[ELSE_LABEL] = else_target

    def __call__(self, state: Any) -> str:
        reg = get_registry()
        for name, _target in self.branches:
            entry = reg.predicates.get(name)
            if entry is None:
                raise LookupError(
                    f"router({self.source!r}) references predicate {name!r}, "
                    f"which is not a registered @predicate"
                )
            if entry.target(state):
                return name
        return ELSE_LABEL


def router(source: str, branches: list[tuple[Any, str]]) -> Router:
    _require_nonempty(source, "router source")
    parsed, else_target = _validate_branches(branches)
    sel = Router(source, parsed, else_target)
    get_registry().routers[source] = RouterEntry(source, parsed, else_target, sel, None, None)
    return sel


def _validate_branches(branches: list[tuple[Any, str]]) -> tuple[tuple[tuple[str, str], ...], str]:
    if not isinstance(branches, (list, tuple)) or not branches:
        raise ValueError("router branches must be a non-empty list of (predicate, target)")
    pairs: list[tuple[str, str]] = []
    else_target: str | None = None
    for pair in branches:
        if not (isinstance(pair, tuple) and len(pair) == 2):
            raise ValueError(f"each branch must be a (predicate, target) pair, got {pair!r}")
        key, target = pair
        _require_nonempty(target, "branch target")
        if key is ELSE:
            if else_target is not None:
                raise ValueError("router has more than one ELSE default; exactly one is required")
            else_target = target
            continue
        _require_nonempty(key, "predicate name")
        if key == ELSE_LABEL:
            raise ValueError(f"predicate name cannot be the reserved label {ELSE_LABEL!r}")
        pairs.append((key, target))
    if else_target is None:
        raise ValueError("router is missing the required ELSE default")
    if not pairs:
        raise ValueError("router needs at least one predicate branch besides ELSE")
    return tuple(pairs), else_target


def _require_nonempty(value: Any, what: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty string, got {value!r}")
```

## Appendix D: `reader.py` recovery rules

A pure `ast` pass over a file read as **text** (never imported). Shapes to handle:

- **Decorators** on `FunctionDef`/`AsyncFunctionDef`/`ClassDef`: walk `decorator_list`.
  - `@node("x")` / `@predicate("x")`: an `ast.Call` whose `func` is `ast.Name(id="node"|"predicate")` or `ast.Attribute(attr="node"|"predicate")`; `key` = `args[0]` (an `ast.Constant` str). `loc.line` = the decorator node's `lineno`.
  - `@state_model` / `@data_model`: bare `ast.Name(id=...)` or `ast.Attribute(attr=...)`; `key` = the class `name`; record `is_graph_state` by which decorator name appears.
- **`lg2m.router(...)`**: an `ast.Call` whose `func` is `ast.Attribute(value=ast.Name(id="lg2m"), attr="router")` (or `ast.Name(id="router")`). `args[0]` = source str; `args[1]` = `ast.List`/`ast.Tuple` of 2-tuples. For each element: target = `elt.elts[1]` (str const); key is the ELSE sentinel iff `elt.elts[0]` is `ast.Attribute(value=ast.Name(id="lg2m"), attr="ELSE")` **or** `ast.Name(id="ELSE")`, else a predicate-name str const. Build `ir.Route(source_id, branches, else_target, loc=SourceLocation(path, call.lineno))`.
- **Non-literal robustness:** if a name/target/source is not an `ast.Constant` str, skip that element (it is the diff layer's diagnostic later), never crash.
- **Merge:** `merge_locations(result, registry)` matches `AnnoRef`/`RouterRef` to registry entries by id/name/source and attaches `SourceLocation(path, line)`; assembly into a `GraphModel` is the diff layer's job, not this one.
