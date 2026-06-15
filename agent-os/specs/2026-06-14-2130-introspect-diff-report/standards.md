# Standards — lg2m layer 2b

The authoritative full text lives under `agent-os/standards/`. This file records which standards
this layer was written against and how each shows up in the code, so a reviewer can check
conformance without re-deriving the selection.

## Adapter — `patterns/adapter.md`
`introspect/base.py` defines the `GraphIntrospector` port and a `FakeIntrospector` adapter. The real
`langgraph_adapter` (layer 3) will be a second adapter behind the same Protocol. Third-party shape is
translated to the IR inside the adapter, never in the core.

## Strategy — `patterns/strategy.md`
`diff/engine.py` organizes the reconciliation as `_CHECKS`, a tuple of uniform
`Callable[[GraphModel, GraphModel, DriftReport], None]` functions — one per category group. Adding a
category is adding a function to the list; no class hierarchy, no visitor.

## Hexagonal architecture — `global/hexagonal-architecture.md`
`reconcile` is a pure function of two IR values: no parse, no introspect, no I/O, no framework. The
assembler (`diff/assemble.py`) is the boundary that turns parser/registry/topology shapes into the
canonical IR the core compares.

## Value objects — `global/value-objects.md`
`DriftItem` is a frozen value object; `DriftReport` is the mutable collector. The engine leans on the
IR's structural identity (`Edge` identity = `(src, dst, predicate)`) so each check is set/dict
arithmetic.

## Error handling + guards — `error-handling/error-handling.md`, `patterns/guards.md`
`_check_meta` confirms only the metadata keys with an introspectable counterpart and skips the rest
(never crashes on an unknown fact). `_fold_diagnostics` maps each single-source `Diagnostic` to a
severity; `--strict` escalates warnings. `canonicalize` guards the single-entry/single-exit composite
contract and emits a diagnostic rather than guessing.

## Testing with fakes — `testing/{testing,mocking}.md`
The `FakeIntrospector` + hand-authored `oracle_topology()` stand in for real introspection so the
engine is exercised end-to-end without the framework. The headline gate is the clean oracle
reconciling to an empty report; every Section 8 category has a focused drift test.

## Carried over — `global/{simplicity,clean-code,coding-conventions}.md`
`from __future__ import annotations`, `str | None` unions, no speculative abstraction, surgical reuse
of the existing parsers and the round-trip assembly seed.
