# Standards — lg2m layer 3

The authoritative full text lives under `agent-os/standards/`. This file records which standards
this layer is written against and how each shows up in the code.

## Adapter — `patterns/adapter.md`
`introspect/langgraph_adapter.py` wraps the framework behind the `GraphIntrospector` port: it reads
`compiled.get_graph(xray=True)` and translates LangGraph's `Graph`/`Edge` shapes into the canonical
IR. It is the single place a third-party type appears; the core never sees one.

## Hexagonal architecture — `global/hexagonal-architecture.md`
The port (`GraphIntrospector`) is owned by the diff core; the Fake and the real adapter are
interchangeable driven adapters. `pipeline.check()` composes ports; it lazy-imports the framework
adapter so the application core (and `import lg2m`) stays framework-free.

## Coupling / cohesion — `global/coupling-cohesion.md`
Framework isolation is the load-bearing boundary: `import lg2m`, `import lg2m.introspect`, and
`import lg2m.pipeline` import no framework (verified by a hermetic subprocess test). Only
`langgraph_adapter` crosses the line, and nothing imports it at module scope.

## Error handling + guards — `error-handling/error-handling.md`, `patterns/guards.md`
`loader.py` treats user code as untrusted: it catches `ImportError`/`AttributeError`/`Exception`
from importing and running the factory and converts them into `ir.Diagnostic(IMPORT_FAILURE, …)`
with a location, rather than letting them escape. `discovery/resolve.py` guards config shape
(missing `graph`/`markdown` → `ConfigError`).

## Factory — `patterns/factory.md`
The pipeline resolves a `"module:callable"` string and invokes the factory to obtain the compiled
graph; `discovery/resolve.py` centralizes that resolution.

## Testing with fakes / mocking — `testing/mocking.md`, `testing/testing.md`
Framework tests are gated with `@pytest.mark.langgraph` and exercise the REAL compiled graph (the
point of this layer is to verify the real `get_graph` shape). The non-framework suite still runs with
`-m "not langgraph"`; the layer-2b Fake remains the unit-level double for the diff engine.

## Carried over — `global/{simplicity,clean-code,coding-conventions}.md`
`from __future__ import annotations`, `str | None` unions, no speculative abstraction; the adapter
feeds the exact `GraphModel` shape the Fake already produced, so the assembler/engine are reused
untouched.
