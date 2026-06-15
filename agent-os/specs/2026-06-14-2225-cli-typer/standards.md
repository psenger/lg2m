# Standards — lg2m layer 4

The authoritative full text lives under `agent-os/standards/`. This file records which standards
this layer is written against and how each shows up in the code.

## Facade — `patterns/facade.md`
`cli.py` is a facade: each command is a small adapter from CLI flags to a single pipeline call
(`pipeline.check` / `pipeline.validate` / `config.loader.load`) plus a renderer (`report.render_*`).
The CLI holds no domain logic; it translates arguments and exit codes.

## Factory — `patterns/factory.md`
`typer.Typer()` constructs the app; the `_resolve_config` / `_load_graphs` / `_resolve_graph_id`
helpers centralize the "turn user input into a validated value or exit 2" construction so the four
commands share one resolution path.

## Coupling / cohesion — `global/coupling-cohesion.md`
The framework-isolation boundary is preserved: `import lg2m.cli` imports no framework. `cli.py`
depends only on `pipeline`, `report`, `config.loader`, and `discovery.resolve`; the only place
langgraph is reachable is the lazy adapter import already inside `pipeline.check`.

## Error handling + guards — `error-handling/error-handling.md`, `patterns/guards.md`
The CLI guards its inputs at the boundary and maps each failure class to an exit code: usage/config
problems (no config, missing file, malformed TOML, unknown/ambiguous graph id, `ConfigError`,
`init` overwrite) → exit 2; drift / structural error → exit 1 via `report.exit_code`; clean → 0.
`pipeline.validate` likewise converts a missing markdown file and an import failure into reported
`DriftItem`s rather than letting exceptions escape.

## Simplicity / clean code / coding-conventions — `global/{simplicity,clean-code,coding-conventions}.md`
`cli.py` stays a thin shell (YAGNI: no `gen`, no skeleton scaffolding, no parent-directory config
walking). `from __future__ import annotations`, `str | None` unions, ruff `E/F/I/UP/B` at
line-length 100. `validate` reuses `DriftItem`/`DriftReport`/renderers rather than inventing a second
output model.

## Testing with fakes / mocking — `testing/testing.md`, `testing/mocking.md`
CLI tests use Typer's `CliRunner` and assert exit codes and output. Tests that run the real compiled
graph are gated `@pytest.mark.langgraph`; the rest run framework-free, so `pytest -m "not langgraph"`
stays green and CLI-test collection imports no framework. `check` is asserted to write nothing.
