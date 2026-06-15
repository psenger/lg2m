# Tech Stack

`lg2m` is a Python package with a CLI, distributed as open source under MIT. It
is designed to be both `pip install`-able as a CLI and importable as a module
from public repos, following current open-source packaging standards.

## Frontend

N/A — there is no GUI. The user-facing surface is a Typer-based CLI
(`init`, `list`, `validate`, `check`, and later `gen` / `sync`) plus text and
JSON drift reports.

## Backend

- **Language:** Python, floor `>=3.10` (matches the `int | bool`-style typing
  used throughout the plan).
- **Build backend:** hatchling, PEP 621 `pyproject.toml`, `src/lg2m/` layout.
- **CLI framework:** Typer.
- **Framework integration (optional):** LangGraph and `langchain-core`, isolated
  behind a `[langgraph]` optional extra. Only `introspect/langgraph_adapter.py`
  imports the framework; the annotated user code imports only `lg2m`'s
  import-light annotation + router module. Development baseline LangGraph 1.2.5 /
  langchain-core 1.4.7 — recent and movable, not a load-bearing pin; the
  supported version *range* is guarded by a CI matrix.

## Database

N/A — `lg2m` is stateless across runs. The only persisted artifact is a future
`.lg2m.lock` baseline-hash file used by the out-of-scope-for-v1 prose `sync`
verb.

## Other

- **Diagram format:** Mermaid `stateDiagram-v2` in Markdown — parsed and emitted
  by `lg2m`'s own parser/emitter (no robust Python `stateDiagram-v2` parser
  exists upstream; LangGraph's `draw_mermaid` emits flowcharts only).
- **Testing:** pytest, with a `@pytest.mark.langgraph` suite for
  framework-dependent tests and golden round-trip fixtures.
- **Linting:** ruff.
- **Distribution:** PyPI, published from CI on tag.
- **License:** MIT (greenfield).
