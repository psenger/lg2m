# Standards for Scaffold + `gen`

The following standards apply to this layer. Each entry is a pointer plus the specific reason
it applies; the full text lives under `agent-os/standards/`.

## Simplicity — global/simplicity.md

YAGNI / KISS. Emit the minimum templates that round-trip; do **not** build the LangChain
`RunnableBranch` emitter until there is an introspector to test it against; no speculative flags
or configurability beyond `--framework` / `--model-style` / `--out`. After each green slice,
apply Kent Beck's four rules (passes tests → reveals intent → no duplication → fewest elements).

## Coding conventions — global/coding-conventions.md

`from __future__ import annotations` at the top of every new module; `str | None` unions;
specific imports (not umbrella packages); one component per file (`generate.py`, `markdown.py`,
`writer.py`). The *generated* code follows the same conventions so it lints clean.

## TDD workflow — global/tdd-workflow.md

Spec-first (this spec), then test-first per phase in vertical slices. The two golden round-trips
are the acceptance tests; write the failing golden before the emitter that satisfies it. Mock
only at boundaries — here the only boundary is the framework, reached via the existing lazy
adapter; the framework-free emitters need no mocks. Commit failing tests before implementation.

## Testing — testing/testing.md, testing/mocking.md

`@pytest.mark.langgraph` marks the two goldens (they import the framework); keep the
framework-free subset runnable with `-m "not langgraph"`. Respect the 90% coverage gate on the
`lg2m` package. Test public interfaces (`generate_code`, `generate_markdown`, the `gen` command),
not private template helpers.

## Facade / Factory — patterns/facade.md, patterns/factory.md

`gen` is a thin façade over `scaffold` (as `check` is over `pipeline`): it turns flags into one
`scaffold` call plus a writer/renderer. `generate_code` / `generate_markdown` are factory-style
entry points that hide the per-file template construction behind a single call.

## Value objects / IR identity — global/value-objects.md, ir/identity.md

Round-trip equality is asserted on IR **identity** fields only (frozen-dataclass `compare`
fields): `Node.id`, `Edge(src_id, dst_id, predicate)`, `Route.branches`/`else_target`,
`Predicate.name`, `DataModel.name`. Carried-but-ignored fields (prose, loc, meta, docstring)
do not participate in the golden assertions.

## Coupling / cohesion — global/coupling-cohesion.md

`scaffold/` depends only on the framework-free surface (`ir`, `parsing`, `diff/assemble`); it
must not import `introspect` or any framework. The `--from-code` direction reaches the framework
**only** through the CLI's reuse of the existing load+introspect chain, preserving the
framework-isolation invariant.
