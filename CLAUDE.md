# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`lg2m` (`langgraph_to_from_mermaid`) is a Python package and CLI that treats a Mermaid
`stateDiagram-v2` (written in Markdown) as a checkable contract for a LangGraph/LangChain
graph, and reports drift in either direction. `docs/design.md` is the authoritative design;
its section numbers are cited throughout the source docstrings ("docs/design.md Section 6",
etc.). `PRIOR-ART.md` is the competitive landscape.

## Commands

The package is installed editable in `.venv`. `tests/conftest.py` also prepends `src/`
to `sys.path`, so the suite runs even without an install.

```bash
source .venv/bin/activate
python -m pytest -q                                          # full suite (231 tests); enforces 90% coverage gate
python -m pytest tests/test_router.py --no-cov -q            # one file  (--no-cov skips the gate)
python -m pytest tests/test_router.py::test_name --no-cov -q # one test
ruff check src tests                                         # lint (must be clean)
```

Coverage is wired into `addopts` (`--cov=lg2m --cov-report=term-missing --cov-fail-under=90`),
so every `pytest` run measures coverage and fails under 90% on the `lg2m` package (currently
~96%). Pass `--no-cov` to skip the gate when running a single file or test.

`ruff check` with no path also scans `examples/`, which intentionally imports the frameworks
and reports import-order findings. Lint `src tests` only.

`pytest.mark.langgraph` marks tests that import the framework — currently
`tests/test_langgraph_adapter.py`. Running them requires `pip install -e ".[langgraph,dev]"`.

## Current state

All layers are shipped and green:

1. IR, config loader, all parsers (`parsing/`)
2. Annotations, router, registry, AST reader, diff engine, report (`diff/`, `report/`)
3. LangGraph introspector behind `[langgraph]` extra (`introspect/`)
4. Typer CLI — `check`, `validate`, `list`, `init`, `gen` (`cli.py`)
5. `gen --from-doc` / `gen --from-code` with round-trip golden tests (`scaffold/`)
6. Prose sync — `sync` verb, lockfile, 3-way merge (`sync/`)

`[project.scripts]` is wired; `lg2m` is on `PATH` after install.

## Architecture

`lg2m check` reconciles three independent sources:

1. **Topology** — `get_graph(xray=True)` on the real compiled graph. The only place
   the frameworks are imported (`introspect/langgraph_adapter.py`, lazy-loaded at call
   time by `pipeline.py`).
2. **Annotations** — `@node`/`@predicate`/`@state_model`/`@data_model` + `lg2m.router`,
   linking each symbol to the diagram. Return their target unchanged at runtime.
3. **The Markdown contract** — a purely topological `stateDiagram-v2` plus GFM tables,
   hidden `<!-- lg2m: ... -->` fences, and `> Note:` blockquotes for facts a diagram
   can't draw (reducers, `Command`/`Send` widths).

### Framework-isolation invariant (load-bearing)

Importing `lg2m` must pull in **no** framework. Only `introspect/langgraph_adapter.py`
may `import langgraph` / `langchain_core`, gated behind the `[langgraph]` extra.
`pipeline.py` imports the adapter lazily so `import lg2m.pipeline` is still
framework-free. `annotations/reader.py` parses user modules with `ast` and never imports
them, so reading a file that imports langgraph does not import langgraph.

### The IR (`ir.py`) — identity is structural

Every value object is a `@dataclass(frozen=True)`. Identity fields drive equality/hashing;
every other field is `field(compare=False)`:

- `Node` identity = `id`
- `Edge` identity = `(src_id, dst_id, predicate)` — `predicate=None` means unconditional;
  two predicates to the same target are two distinct edges.
- `Predicate` identity = `name`; `Route` keyed by `source_id`; `DataModel` by `name`.

`GraphModel` is the one mutable, non-identity container (the parse-then-assemble buffer).
`Node.meta` is a mutable dict on a frozen instance — build the dict first, then construct
the `Node`; never mutate `node.meta` afterward.

`ELSE_LABEL = "[else]"` lives in `ir.py` and is the single literal shared by the mermaid
parser, the router, and the decorators.

### The routing model — why routing can't drift

`lg2m.router(source, branches)` (`annotations/router.py`) is a factory. From one ordered
`[(predicate_name, target), …, (ELSE, target)]` mapping it generates the LangGraph `path_fn`
and owns the `path_map`. The selector resolves predicate names to `@predicate` functions
lazily from the registry at call time. `ELSE` is a sentinel (`lg2m.ELSE`); exactly one
required default. A missing `[else]` or a predicate literally named `[else]` is rejected
at construction.

### Annotations: two authorities, merged

- `annotations/registry.py` — module-level singleton; the authority on "this symbol is
  live." Reset between graphs and between tests via the autouse `reset_registry` fixture in
  `conftest.py`.
- `annotations/reader.py` — AST pass; the authority on `file:line`. `merge_locations`
  joins the two: attaches the reader's `SourceLocation` to each registry entry. A
  non-literal argument is skipped (never guessed, never raised on).

### Parsing (`parsing/`)

lg2m owns its Mermaid parser/emitter — no third-party library. `mermaid.py` is a line
classifier with a composite-state stack; classification order matters (composite close,
composite open, pseudostate decl, transition) because several line kinds share the `state `
prefix. The round-trip contract is structural, not byte-exact: `parse(emit(parse(x)))`
preserves edge order and nesting. `markdown.py` is a forward line scanner (not a full AST).
`tables.py` handles GFM tables with `\|` escaping; `meta.py` decodes the three metadata
mechanisms (table / fence / note).

### Orchestration and pipeline

`pipeline.py` wires the layers end-to-end for `check`: config → resolve → load (runs user
code) → introspect → read annotations → assemble both sides → reconcile → `DriftReport`.
`diff/assemble.py` builds the two comparable `GraphModel`s; `diff/engine.py` reconciles
them; `report/text.py` and `report/json.py` render the `DriftReport`.

`sync/engine.py` drives the `sync` verb: framework-free prose sync that reads source
docstrings and Markdown via AST/text scanning (never imports user code). `sync/lockfile.py`
manages the `.lg2m.lock` baseline; `sync/merge.py` performs the 3-way merge.

`scaffold/generate.py` emits annotated LangGraph code from a doc-side `GraphModel`;
`scaffold/markdown.py` emits a Markdown contract skeleton from a code-side `GraphModel`.

## Conventions

- `from __future__ import annotations` at the top of every module; `X | None` unions,
  `requires-python >= 3.10`.
- TOML config lives under `[tool.lg2m.graphs.<id>]` in either `pyproject.toml` or a
  standalone `lg2m.toml`. `config/loader.py` uses stdlib `tomllib` with a `tomli` fallback
  for 3.10.
- `agent-os/standards/` holds the coding standards this project is written against (SOLID,
  clean-code, TDD, design-pattern catalog). Consult the relevant one when a change touches
  its area.
