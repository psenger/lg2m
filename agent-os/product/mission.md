# Product Mission

## Problem

A LangGraph (or LangChain LCEL) graph and the Mermaid `stateDiagram-v2`
diagram that documents it drift apart the moment either one changes. Today no
tool keeps a graph's *topology* and a human-readable Mermaid *contract* in
agreement bidirectionally, detects drift as a build-time failure, and can
scaffold either side from the other.

Every individual capability exists only in isolation:

- One-way code -> diagram (LangGraph's own `draw_mermaid`, LangGraph Studio,
  `python-statemachine` / `transitions` exports, the general-purpose *Mermaid
  Diagram Sync* GitHub app).
- Build-then-run builders (LangGraph-GUI).

None combines bidirectional topology sync with drift-as-a-build-contract, and
none is LangGraph-aware. Conditional routing is the worst offender: neither
framework exposes per-branch condition logic to introspection, so the routing
shown in a diagram has nothing stopping it from lying about what the runtime
actually does.

## Target Users

Python developers who build and maintain **LangGraph** graphs (and the
LCEL-expressible slice of **LangChain**: linear chains + `RunnableBranch`) and
who keep a Mermaid `stateDiagram-v2` diagram in Markdown as the human-facing
contract for that graph. They want the diagram to be trustworthy enough to
review in a PR and to fail CI when it no longer matches the code.

## Solution

`lg2m` makes the diagram and the code provably agree by reconciling three
sources and owning the one that normally drifts:

- **Introspection is the source of truth for graph shape.** `lg2m` reads the
  real compiled object (`get_graph()` + the state schema) for nodes, edges,
  conditional flags, `path_map` targets, and reducers.
- **Annotations link code to the diagram and Markdown.** `@node`, `@predicate`,
  `@state_model` / `@data_model` record metadata and return their target
  unchanged.
- **Routing is a generated, per-edge predicate model (Model A).** A conditional
  fan-out is authored once as an ordered `[(predicate, target), ..., (ELSE,
  target)]` mapping; `lg2m` generates the router and owns the `path_map`, so the
  diagram labels, the runtime router, and the `path_map` are one source and
  cannot drift. Model A is the only routing representation that compiles cleanly
  to **both** frameworks (a `path_fn` for LangGraph, a 1:1 `RunnableBranch` for
  LangChain).

The Mermaid diagram is purely topological; anything it cannot draw (reducers,
`Send` fan width, `Command(goto)` nuance) lives in structured Markdown metadata.
`lg2m` reports drift with code and doc `file:line` locations plus hints, and
scaffolds either side from the other.

The novelty is the combination — bidirectional, drift-detecting, LangGraph-aware
sync with a routing model that is 1:1 with both frameworks — not any single
capability.
