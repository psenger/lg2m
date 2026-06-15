# Foundation Layer — IR + Config + Markdown/Mermaid Parsing

**Spec folder (created by Task 1):** `agent-os/specs/2026-06-14-1642-foundation-ir-parsing/`

## Context

`lg2m` (langgraph_to_from_mermaid) is a greenfield Python package whose product
roadmap Phase 1 MVP is **`lg2m check`: drift detection for LangGraph**. `docs/design.md`
Section 13 orders that MVP as four build layers; this spec implements **layer 1
only — the framework-free foundation**: the intermediate representation, the
config loader, and the Markdown + `stateDiagram-v2` parsers/emitters. No
`langgraph` / `langchain_core` import appears anywhere in this layer.

Why this scope: the IR is the shared contract every later layer (annotations,
introspection, diff, CLI) builds on, and the `stateDiagram-v2` parser is the
"substantial, bug-prone" piece `docs/design.md` calls out (no robust Python parser
exists to reuse). Cutting the spec at the framework boundary makes it fully
testable in one session against a concrete oracle: the already-authored golden
fixture `examples/support_pipeline/docs/support_pipeline.md` (+ its `lg2m.toml`),
which crosses every hard case once — a parallel fork/join, a generated
conditional fan-out with a required `[else]`, an `investigate` composite state,
a `Send` map-reduce edge, a `Command(goto)` edge, three reducer kinds, and all
three metadata mechanisms. The foundation succeeds when that fixture parses into
the expected `GraphModel` and the diagram survives a parse->emit->parse cycle
without structural loss. This unblocks layers 2-4.

The package is established at design stage only: no `src/lg2m/`, no
`pyproject.toml`, no `tests/`. Everything below is new.

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
- New pattern / real uncertainty: `src/lg2m/parsing/mermaid.py` hand-writes a `stateDiagram-v2` parser **and** emitter covering `[else]`, `<<fork>>` / `<<join>>` pseudostate declarations, and composite/nested states; no robust Python parser exists to reuse.
- Architectural / cross-cutting: `src/lg2m/ir.py` is the value-object contract (`Node`/`Edge`/`Predicate`/`Route`/`DataModel`/`Meta`/`Diagnostic`/`GraphModel`) with non-obvious identity rules (`Edge` identity = `(src_id, dst_id, predicate)`); errors propagate to every later layer.
- Surface area: 7 implementation modules (`pyproject`, `ir`, `config/loader`, `parsing/{mermaid,markdown,tables,meta}`) plus matching test modules.
- Bounded by a concrete oracle (why 4, not 5): `examples/support_pipeline/docs/support_pipeline.md` + `lg2m.toml` already exist as the golden fixture, removing open-ended uncertainty.

**Model Recommendation:** Opus
**Reason:** the Mermaid parser/emitter phase needs careful edge-case reasoning; staying in one model keeps continuity across the IR contract and the parsers.

**Context note:** If context tightens mid-run, **Phase 3 (Mermaid parser) is the natural split point** — start a fresh session there. Phases 1-2 and 4 are mechanical relative to Phase 3.

## Standards

Apply these (selected in `/inject-standards`; full text copied into `standards.md` by Task 1):
- `@agent-os/standards/global/value-objects.md` — the IR is value objects with explicit identity.
- `@agent-os/standards/global/simplicity.md`, `@agent-os/standards/global/clean-code.md` — minimal, no speculative abstraction (no builder, no AST library).
- `@agent-os/standards/global/coding-conventions.md` — Python naming/conventions for a public MIT package.
- `@agent-os/standards/testing/testing.md`, `@agent-os/standards/testing/mocking.md` — pytest layout, golden fixtures (no mocking needed in this framework-free layer).
- `@agent-os/standards/global/hexagonal-architecture.md`, `@agent-os/standards/patterns/adapter.md`, `@agent-os/standards/global/coupling-cohesion.md` — relevant as a forward constraint: keep this layer free of any framework import so the later introspection adapter is the only seam.
- `@agent-os/standards/patterns/decorator.md` — informs the deferred `__init__` export surface (layer 2).

## Acceptance Criteria

Stable ids; `### Done when` blocks reference them. All counts/shapes are read from the real fixture (`examples/support_pipeline/docs/support_pipeline.md`, `examples/support_pipeline/lg2m.toml`).

- **AC-01 (config from pyproject).** Given a `pyproject.toml` with `[tool.lg2m.graphs.<id>]`, When `config.loader.load()` reads it, Then it returns `{<id>: {...}}` preserving `graph`, `markdown`, `sys_path`, `xray`.
- **AC-02 (config from standalone toml).** Given `examples/support_pipeline/lg2m.toml`, When loaded, Then `support_pipeline` maps to `graph == "support_pipeline.graph:build_graph"`, `markdown == "docs/support_pipeline.md"`, `sys_path == ["src"]`, `xray is True`. A pyproject `[tool.lg2m]` and a standalone `lg2m.toml` with the same content produce identical mappings.
- **AC-03 (TOML 3.10 shim).** Given Python 3.10 (no stdlib `tomllib`), When the loader imports, Then it falls back to `tomli`; on 3.11+ it uses stdlib `tomllib` with no extra dependency. TOML files are opened in binary mode.
- **AC-04 (frontmatter).** Given the fixture, When parsed, Then `GraphModel.graph_id == "support_pipeline"` from the `lg2m_graph` frontmatter key.
- **AC-05 (diagram states).** Given the mermaid block, When parsed, Then the named states are exactly: `ingest_ticket, fork_enrich, join_enrich, fetch_history, lookup_account, classify_intent, escalate_to_human, auto_resolve, investigate, gather_logs, analyze, map_items, process_item, reduce_items, compose_reply` (15; `[*]` is not a node).
- **AC-06 (fork/join pseudostates).** Given `state fork_enrich <<fork>>` / `state join_enrich <<join>>` declaration lines, When parsed, Then `fork_enrich` carries pseudostate `fork` and `join_enrich` carries `join`; neither is read as a transition.
- **AC-07 (conditional fan-out + else + route).** Given the three `classify_intent --> ...` lines, When parsed, Then there are exactly 3 conditional edges: `should_escalate -> escalate_to_human`, `should_auto_resolve -> auto_resolve`, `[else] -> investigate` (with `is_else == True`); and exactly one `Route(source_id="classify_intent", branches=(("should_escalate","escalate_to_human"),("should_auto_resolve","auto_resolve")), else_target="investigate")`.
- **AC-08 (composite/subgraph).** Given `state investigate { ... }`, When parsed, Then `investigate.is_subgraph == True` and its 3 internal edges (`[*] -> gather_logs`, `gather_logs -> analyze`, `analyze -> [*]`) are captured in the `investigate` scope.
- **AC-09 (start/end by position).** Given top-level `[*] --> ingest_ticket` and `compose_reply --> [*]`, When parsed, Then left `[*]` resolves to START and right `[*]` to END; composite-internal `[*]` resolve to `investigate`'s local start/end, never coalesced with the top-level ones.
- **AC-10 (Send/Command are plain diagram edges).** Given `map_items --> process_item` and `escalate_to_human --> compose_reply`, When parsed, Then both are ordinary unconditional edges (`predicate is None`, `conditional == False`); their Send/Command nature exists only as metadata (AC-13), not diagram syntax.
- **AC-11 (data models + reducers).** Given `## Data Models`, When parsed, Then `models` has `PipelineState` (8 attributes, `is_graph_state == True` — its prose carries `@state_model`) and `Ticket` (4 attributes, `is_graph_state == False`); reducer names resolve to `add_messages` on `messages`, `operator.add` on `attempts` and `enrichment`, `extend_unique` on `item_results`, and `None` on `ticket/flags/items/resolution` and all four `Ticket` attributes. (`DataModel.style` — TypedDict vs BaseModel — is a code-side fact set by the later introspection layer, not encoded in the markdown, so it is not asserted at this layer.)
- **AC-12 (escaped pipe in table cell).** Given the `Ticket` rows whose descriptions contain `` `'low'` \| `'normal'` \| `'high'` `` and `` `'free'` \| `'pro'` \| `'enterprise'` ``, When `tables.py` parses them, Then each row has exactly 4 cells and the description cell contains literal `|`, not extra columns.
- **AC-13 (three metadata mechanisms).** Given the `###` node blocks, When `meta.py` parses, Then it yields: a TABLE meta on `ingest_ticket`; FENCE metas on `classify_intent`, `escalate_to_human`, `map_items`, `reduce_items`; and a NOTE meta on `map_items`. `map_items` owns **both** a FENCE and a NOTE (two `Meta` entries, same `owner_id`), so `GraphModel.meta` is a flat list. Total = 6 meta items.
- **AC-14 (fence payload decode).** Given `<!-- lg2m: channel=enrichment; reducer=operator.add; merges=fetch_history,lookup_account -->`, When parsed, Then it decodes to `{"channel":"enrichment","reducer":"operator.add","merges":"fetch_history,lookup_account"}`; and `merges=process_item (Send)` keeps the trailing `(Send)` in the value (split pairs on `;`, key/value on first `=` only).
- **AC-15 (mermaid structural round-trip).** Given the mermaid block, When `parse(block)` then `emit` then `parse` again, Then the two models are structurally equal on: set of node ids, each node's `is_subgraph` + pseudostate, and the ordered edge list `(src_id, dst_id, predicate, is_else, conditional)`. Byte-exact text equality is **not** required.
- **AC-16 (IR identity).** Given `Edge("classify_intent","escalate_to_human","should_escalate")` vs `Edge("classify_intent","auto_resolve","should_auto_resolve")`, When compared, Then same-key edges are equal and hash-equal and two predicates to the same target are distinct edges; given two `Node("investigate", ...)` differing only in `meta`/`prose`, Then they are equal (identity by `id`); a frozen instance rejects attribute rebinding.
- **AC-17 (Index table).** Given `## Index`, When parsed, Then it has 15 rows = 13 `node` ids + 2 `predicate` ids; the predicate ids are `{should_escalate, should_auto_resolve}`; `fork_enrich` / `join_enrich` are **absent** from the Index (they are diagram pseudostates, distinct from the Index node ids even though both surfaces total 15 names).
- **AC-18 (Edges table).** Given `## Edges`, When parsed, Then 17 rows are read with columns `from/to/label/kind/notes`; blank `label` cells become `""` (not `None`); the `-`-free label column distinguishes the 3 conditional rows (`should_escalate`, `should_auto_resolve`, `[else]`) from the 14 unlabelled rows.

## Tasks

> Gate style: **Done-when + Acceptance criteria.** Each task's `### Done when` lists concrete checks; where an AC applies it is named ("AC-NN satisfied"). Each subtask is independently completable in under 2 hours. `pytest` runs from the repo root; `ruff check src tests` must stay clean throughout.

## Task 1: Save Spec Documentation

- [x] Create `agent-os/specs/2026-06-14-1642-foundation-ir-parsing/` containing:
  - `plan.md` — this plan (Context through Verification).
  - `shape.md` — the scope, decisions, and the AC-01..AC-18 list (the `## Acceptance Criteria` block above, verbatim).
  - `standards.md` — full text of each standard listed under `## Standards` (read each `@agent-os/standards/...` file and inline it).
  - `references.md` — `examples/support_pipeline/` (annotated golden, the oracle) and `examples/support_pipeline_native/` (runnable LangGraph/LangChain baseline), with the key files and what to borrow.
  - `visuals/` — empty (none; CLI + library).

### Done when
- [x] All five entries exist under the spec folder and `plan.md`/`shape.md`/`standards.md`/`references.md` are non-empty.
- [x] `shape.md` contains AC-01 through AC-18 verbatim.

- [x] **Phase 1: Project scaffold, IR, config**

  - [x] **Task 1.1: `pyproject.toml` + project skeleton**
    - [x] PEP 621 `pyproject.toml`, hatchling build backend, `src/` layout, `requires-python = ">=3.10"`.
    - [x] Conditional runtime dep `tomli >= 2.0 ; python_version < "3.11"`; declare an unused `[project.optional-dependencies] langgraph` extra; dev deps `ruff`, `pytest`.
    - [x] `[tool.pytest.ini_options]` (testpaths, a `langgraph` marker reserved for later layers); minimal `[tool.ruff]`.
    - [x] Create empty `src/lg2m/parsing/__init__.py`, `src/lg2m/config/__init__.py`, `tests/` tree.

    ### Done when
    - [x] `pip install -e .` resolves in a clean venv on the host Python.
    - [x] `ruff check` runs (clean on the empty skeleton).

  - [x] **Task 1.2: `src/lg2m/ir.py`**
    - [x] Implement the value objects and enums per **Appendix A** (frozen dataclasses; identity enforced via `field(compare=False)` on non-identity fields; `GraphModel` non-frozen container).
    - [x] Module docstring documents the identity rules and the "build `meta` dict, then construct the frozen `Node`" discipline.
    - [x] `tests/test_ir.py` covering identity/hash and frozen-rebind rejection.

    ### Done when
    - [x] AC-16 satisfied.
    - [x] `pytest tests/test_ir.py` green; `ruff check src/lg2m/ir.py` clean.

  - [x] **Task 1.3: `src/lg2m/__init__.py` export surface (stub)**
    - [x] Re-export the IR names this layer needs; add `__all__`.
    - [x] Add `# TODO(layer-2)` for the deferred public API (`node`, `predicate`, `router`, `ELSE`, `state_model`, `data_model`) — those land with the annotations layer; importing names that do not exist yet would break `import lg2m`.

    ### Done when
    - [x] `python -c "import lg2m"` succeeds and exposes the IR names.
    - [x] `ruff check src/lg2m/__init__.py` clean.

  - [x] **Task 1.4: `src/lg2m/config/loader.py`**
    - [x] `load(path) -> dict[str, dict]` handling both `[tool.lg2m.graphs.*]` in a `pyproject.toml` and a standalone `lg2m.toml`; binary-mode open; `tomllib`/`tomli` import shim.
    - [x] `tests/test_config_loader.py` against the real `examples/support_pipeline/lg2m.toml`.

    ### Done when
    - [x] AC-01, AC-02, AC-03 satisfied.
    - [x] `pytest tests/test_config_loader.py` green; `ruff check` clean.

- [x] **Phase 2: Markdown container parsing**

  - [x] **Task 2.1: `parsing/tables.py` — parse**
    - [x] GFM table reader (header / `---` delimiter / body rows) with a char-scanning splitter that treats `\|` as a literal pipe.
    - [x] `tests/test_tables.py` parsing the Index (15 rows), a Data Models table (8 and 4 rows), and the Edges table (17 rows).

    ### Done when
    - [x] AC-12 satisfied; Index/Data-Models/Edges row counts assert correctly.
    - [x] `pytest tests/test_tables.py` green; `ruff check` clean.

  - [x] **Task 2.2: `parsing/tables.py` — emit**
    - [x] `(headers, rows) -> GFM lines`, re-escaping `|` as `\|`; alignment minimal (structural round-trip, not byte-exact).

    ### Done when
    - [x] emit->parse of the `Ticket` table yields identical row dicts.
    - [x] `ruff check` clean.

  - [x] **Task 2.3: `parsing/markdown.py` — frontmatter + section split**
    - [x] Forward line scanner: parse `---` frontmatter (`lg2m_graph`), then split the 6 canonical `##` sections (`Index`, `Graph`, `Data Models`, `Predicates`, `Nodes`, `Edges`), retaining unknown sections verbatim. Track `(section, current_id, line_no)` for `SourceLocation`.

    ### Done when
    - [x] AC-04 satisfied; the 6 sections are located with correct line ranges.
    - [x] `pytest tests/test_markdown.py` green; `ruff check` clean.

  - [x] **Task 2.4: `parsing/markdown.py` — per-id prose + mermaid-block locator**
    - [x] Split `###` sub-sections (strip backticks from ids); collect prose excluding tables/fences/notes; return the inner mermaid block text + start line.

    ### Done when
    - [x] Prose for `should_escalate` excludes its non-prose lines; the mermaid block inner text + start line are returned.
    - [x] `ruff check` clean.

  - [x] **Task 2.5: `parsing/meta.py` — the three mechanisms**
    - [x] TABLE (`| meta | value |` via `tables.py`), FENCE (`<!-- lg2m: k=v; k=v -->`, split on `;` then first `=`), NOTE (`> Note:` collector). Append `Meta` items to a flat list keyed by `owner_id`.
    - [x] `tests/test_meta.py`.

    ### Done when
    - [x] AC-13, AC-14 satisfied (including `map_items` owning both FENCE and NOTE).
    - [x] `pytest tests/test_meta.py` green; `ruff check` clean.

- [x] **Phase 3: Mermaid parse/emit** (context split point — see Complexity note)

  - [x] **Task 3.1: line classifier + transitions**
    - [x] Strip the `stateDiagram-v2` header, blank lines, and `%% ...` comments; classify transitions: unconditional `a --> b`, labelled `a --> b: pred`, and the reserved `[else]` label (`is_else=True`, `predicate="[else]"`). Split on the first `:` after `-->`, strip both sides.

    ### Done when
    - [x] AC-07, AC-10 satisfied for the top-level transitions.
    - [x] `pytest tests/test_mermaid.py` (transitions subset) green; `ruff check` clean.

  - [x] **Task 3.2: fork/join declaration lines**
    - [x] Recognize `state <id> <<fork>>` / `<<join>>` as pseudostate declarations (`Node.meta["pseudostate"]`), classified before the transition pattern; a `state `-prefixed line matching nothing is a `PARSE_ERROR` diagnostic, not a silent drop.

    ### Done when
    - [x] AC-06 satisfied; no fork/join line is misread as a transition.
    - [x] `ruff check` clean.

  - [x] **Task 3.3: composite-state stack + scoped `[*]`**
    - [x] `state <id> {` pushes a scope (mark `is_subgraph`), `}` pops; classify composite-open before fork/join before transition; map `[*]` to START/END by position within the current scope; enforce a nesting-depth limit (unbalanced `}` at depth 0 = `PARSE_ERROR`).

    ### Done when
    - [x] AC-08, AC-09 satisfied; nested `[*]` belong to `investigate`.
    - [x] `ruff check` clean.

  - [x] **Task 3.4: emit + structural round-trip**
    - [x] Deterministic emit order: `stateDiagram-v2`, pseudostate declarations, composite blocks (indented inner edges), then top-level edges in parse order; labelled vs unlabelled formatting.

    ### Done when
    - [x] AC-15 satisfied (`parse == parse(emit(parse))` on structural fields).
    - [x] `pytest tests/test_mermaid.py` green; `ruff check` clean.

- [x] **Phase 4: Round-trip integration against the golden fixture**

  - [x] **Task 4.1: assemble `GraphModel` from the fixture**
    - [x] `tests/test_round_trip_support_pipeline.py` wires markdown + tables + meta + mermaid into one `GraphModel` from `examples/support_pipeline/docs/support_pipeline.md` and asserts the structural fields (graph_id, state_model_name, the 15 states, fork/join, the 3 conditional edges + the single Route, the 2 data models with reducer names, the 6 meta items).

    ### Done when
    - [x] AC-04, AC-05, AC-06, AC-07, AC-08, AC-11, AC-13, AC-17, AC-18 satisfied against the real file.
    - [x] `ruff check tests` clean.

  - [x] **Task 4.2: mermaid structural round-trip on the fixture block**
    - [x] Same suite: extract the fixture's mermaid block and assert AC-15.

    ### Done when
    - [x] AC-15 satisfied against the fixture's actual block.

  - [x] **Task 4.3: full-suite gate**
    - [x] Run the whole suite and the linter; confirm the parsers write nothing (pure/read-only).

    ### Done when
    - [x] `pytest tests/ -q` all green; `ruff check src tests` clean.
    - [x] No test creates or modifies any file on disk.

## Critical Files

New (this layer):
- `src/lg2m/ir.py` — value-object IR (full reference in Appendix A); the load-bearing contract.
- `src/lg2m/parsing/mermaid.py` — highest-risk module (parser/emitter + composite stack).
- `src/lg2m/parsing/meta.py` — the three metadata mechanisms; `GraphModel.meta` is a flat list because `map_items` owns two.
- `src/lg2m/parsing/markdown.py`, `src/lg2m/parsing/tables.py` — document container + GFM tables (escaped-pipe aware).
- `src/lg2m/config/loader.py` — `[tool.lg2m]` / `lg2m.toml` with the `tomllib`/`tomli` shim.
- `pyproject.toml`, `src/lg2m/__init__.py`.

Oracle (read-only, do not modify):
- `examples/support_pipeline/docs/support_pipeline.md` — every AC count/shape is drawn from this file.
- `examples/support_pipeline/lg2m.toml` — config-loader fixture for AC-01/02/03.

Design of record: `docs/design.md` Sections 5 (layout), 6 (IR), 7 (Markdown contract).

## Verification

End-to-end, framework-free, from the repo root:

1. `pip install -e .` in a clean venv (resolves on 3.10 via `tomli`, on 3.11+ via stdlib `tomllib`).
2. `pytest tests/ -q` — all green, including `tests/test_round_trip_support_pipeline.py`, which is the acceptance gate: the golden fixture parses into the expected `GraphModel` (AC-04/05/06/07/08/11/13/17/18) and the diagram round-trips structurally (AC-15).
3. `ruff check src tests` — clean.
4. Confirm no test wrote to disk (the parsers are pure functions over text).

A negative check to add opportunistically: a copy of the fixture with the `[else]` branch deleted should surface a `MISSING_ELSE`-shaped condition (a missing `else_target` on the `classify_intent` route) — full `MISSING_ELSE` diagnostics belong to the diff layer, but the foundation should at least represent the absence faithfully.

## Appendix A: `ir.py` reference implementation

```python
"""Intermediate representation for lg2m: framework-free value objects.

Identity rules (docs/design.md Section 6) are enforced structurally:
  Node      identity = id
  Edge      identity = (src_id, dst_id, predicate)   # predicate None => unconditional
  Predicate identity = name
  Route     keyed by source_id in GraphModel.routes
  DataModel keyed by name in GraphModel.models

Frozen + compare=False covers only the identity fields in equality/hash;
everything else (prose, loc, meta, ...) is carried but not part of identity.
GraphModel is the only mutable, non-identity container. Build a Node's `meta`
dict first, then construct the frozen Node; never mutate it afterward.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeKind(str, Enum):
    NODE = "node"
    START = "start"
    END = "end"


class MetaKind(str, Enum):
    TABLE = "table"    # visible key/value table under an entity heading
    FENCE = "fence"    # hidden  <!-- lg2m: k=v; k=v -->
    NOTE = "note"      # free-text  > Note: ...


class DiagnosticKind(str, Enum):
    COMMAND_WITHOUT_DESTINATIONS = "command_without_destinations"
    SEND_WITHOUT_DESTINATIONS = "send_without_destinations"
    NON_ENUMERABLE_TARGETS = "non_enumerable_targets"
    IMPORT_FAILURE = "import_failure"
    MISSING_ELSE = "missing_else"
    ROUTER_NOT_WIRED = "router_not_wired"
    PARSE_ERROR = "parse_error"   # foundation layer: malformed markdown/mermaid/toml


@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    col: int | None = None


@dataclass(frozen=True)
class Node:
    id: str
    kind: NodeKind = field(compare=False, default=NodeKind.NODE)
    is_subgraph: bool = field(compare=False, default=False)
    anno_id: str | None = field(compare=False, default=None)
    prose: str | None = field(compare=False, default=None)
    docstring: str | None = field(compare=False, default=None)
    meta: dict[str, Any] = field(compare=False, default_factory=dict)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Edge:
    src_id: str
    dst_id: str
    predicate: str | None = None          # part of identity; None => unconditional
    conditional: bool = field(compare=False, default=False)
    is_else: bool = field(compare=False, default=False)
    parallel: bool = field(compare=False, default=False)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Predicate:
    name: str
    prose: str | None = field(compare=False, default=None)
    docstring: str | None = field(compare=False, default=None)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Route:
    source_id: str
    branches: tuple[tuple[str, str], ...]   # ordered (predicate_name, target_id)
    else_target: str
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Attribute:
    name: str
    type_str: str
    reducer: str | None = None
    description: str | None = field(compare=False, default=None)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class DataModel:
    name: str
    style: str                              # "TypedDict" | "BaseModel" | ...
    is_graph_state: bool = field(compare=False, default=False)
    anno: str | None = field(compare=False, default=None)
    attributes: tuple[Attribute, ...] = field(compare=False, default=())
    prose: str | None = field(compare=False, default=None)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Meta:
    owner_id: str
    kind: MetaKind
    data: Any                               # dict for TABLE/FENCE, str for NOTE
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Diagnostic:
    kind: DiagnosticKind
    subject: str
    message: str
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass
class GraphModel:
    graph_id: str
    origin: str                             # "markdown" | "code" | "merged"
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    predicates: dict[str, Predicate] = field(default_factory=dict)
    routes: dict[str, Route] = field(default_factory=dict)
    models: dict[str, DataModel] = field(default_factory=dict)
    meta: list[Meta] = field(default_factory=list)
    state_model_name: str | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
```

Design notes carried from the design pass: `Edge` with `predicate=None` distinguishes the unlabelled fork/join edges by `(src, dst)`; the `[else]` branch stores `predicate="[else]"`, `is_else=True` so it stays a distinct identity and round-trips its label; `Route.branches` and `DataModel.attributes` are tuples so the frozen instances stay hashable and order-significant; `compose=False` on a non-identity field is the single most likely silent-bug source, so AC-16's identity test runs first.
