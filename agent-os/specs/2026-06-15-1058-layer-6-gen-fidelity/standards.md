# Standards for Layer 6 — `gen` fidelity

The following standards apply to this layer. Each entry is a pointer plus the specific reason it
applies; the full text lives under `agent-os/standards/`.

## Simplicity — global/simplicity.md

YAGNI / KISS. `decanonicalize` reconstructs only the sugar the example needs (single-level composites,
fork/join, `[*]`); do not generalise to N-level nesting or reconstruct Send width / `Command(goto)`
statically — keep those metadata-driven and documented as lossy. The LangChain emitter mirrors only the
LCEL-expressible slice. Apply Kent Beck's four rules after each green slice.

## TDD workflow — global/tdd-workflow.md

Spec-first (this spec), then test-first per phase in vertical slices. The strict bidirectional round-trips
(AC-1, AC-2) are the acceptance tests — write the failing golden before the emitter that satisfies it.
Promote the lenient smokes to strict goldens *before* implementing the inverse. Commit failing tests first.

## Testing — testing/testing.md, testing/mocking.md

`@pytest.mark.langgraph` marks the goldens and the LangChain build test (they import the framework); keep
the framework-free subset runnable with `-m "not langgraph"` (AC-7, AC-9). Respect the 90% coverage gate
on `lg2m` (AC-10). Test public interfaces (`generate_code`, `generate_markdown`, `decanonicalize`, the
`gen` command), not private template helpers. Mock only at the framework boundary, reached via the
existing lazy adapter.

## IR identity / value objects — ir/identity.md, global/value-objects.md

Round-trip equality is asserted on IR **identity** fields only (`structural_key`): `Node.id`,
`Edge(src_id, dst_id, predicate)`, `Route.branches`/`else_target`, `Predicate.name`, `DataModel` name +
attributes. The inverse must preserve these exactly; carried fields (prose, loc, meta, docstring) are
ignored by the goldens. Build `Node.meta` before constructing the frozen `Node`; never mutate after.

## DRY / orthogonality — global/dry-orthogonal-arity.md

`decanonicalize` is the literal inverse of `canonicalize`; read the forward Rules A/B/C as the single
source of truth and mirror them rather than re-deriving the topology rules. The LangChain `RunnableBranch`
and the LangGraph `path_fn` both derive from the **one** `Route.branches` mapping — one mapping, two
emissions, no drift.

## Coupling / cohesion — global/coupling-cohesion.md

`scaffold/` and `diff/decanonicalize` depend only on the framework-free surface (`ir`, `parsing`,
`diff/assemble`); they must not import `introspect` or any framework (AC-9). The `--from-code` direction
reaches the framework only through the CLI's reuse of the existing load+introspect chain, preserving the
framework-isolation invariant.

## Composition — global/composition.md  (Phase 2 only)

LCEL composition for the LangChain emitter: `RunnableSequence` (`|`) for chain edges, `RunnableParallel`
+ a `RunnableLambda` hand-merge for fan-out (no channel reducer), `RunnableBranch` for conditional routing
with arms in predicate order and `[else]` last.

## SOLID / clean-code — global/solid.md, global/clean-code.md

SRP for the new transform and emitter (one module, one responsibility); OCP via the `framework` parameter
selecting the emission strategy without rewriting the shared IR walk. Naming in the generated code matches
the example (`build_<parent>_subgraph`, `fan_out_<x>`, `route_<source>`) so it lints clean and reads like
the hand-written `examples/support_pipeline/`.
