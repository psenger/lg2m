# Design: `langgraph_to_from_mermaid` (`lg2m`)

> A Python package + CLI (MIT, greenfield) that keeps a **Mermaid `stateDiagram-v2` in Markdown** in agreement with a **native LangGraph or LangChain graph**: full bidirectional fidelity for LangGraph, and the LCEL-expressible slice (linear chains + `RunnableBranch`) for LangChain. lg2m introspects the real compiled object for topology truth, reads code **annotations** that link each symbol to the diagram and Markdown, and owns conditional routing through a **generated, per-edge predicate model** so the diagram and the runtime routing cannot drift. The Mermaid diagram is purely topological; anything it cannot draw lives in structured Markdown metadata. lg2m reports drift with locations and hints, and scaffolds either side from the other.

This product is 100% open source MIT licensed result. It should be correctly built to be both installed as a CLI and a Downloadable Module in Public Repos. All documentation naming conventions and code should adhere to open standards, with max flexibility and conformation to something that would be of the highest open source standard.

## Standards

These standards apply to all lg2m work; paths resolve at read time so they stay in sync (see `agent-os/standards/`).

**Framework isolation (the introspector boundary):**
@agent-os/standards/global/hexagonal-architecture.md
@agent-os/standards/patterns/adapter.md
@agent-os/standards/global/coupling-cohesion.md

**Testing strategy:**
@agent-os/standards/testing/testing.md
@agent-os/standards/testing/mocking.md

**Code restraint & conventions:**
@agent-os/standards/global/simplicity.md
@agent-os/standards/global/clean-code.md
@agent-os/standards/global/coding-conventions.md

**IR & annotations:**
@agent-os/standards/global/value-objects.md
@agent-os/standards/patterns/decorator.md

## 1. Context and how we got here

No tool provides bidirectional, drift-detecting sync between a LangGraph/LangChain graph's *topology* and a human-readable Mermaid `stateDiagram-v2` *contract*, with scaffolding in either direction. Every individual capability exists in isolation: one-way code -> diagram (LangGraph's own `draw_mermaid`, LangGraph Studio, the `python-statemachine` / `transitions` exports, and the general-purpose *Mermaid Diagram Sync* GitHub app that regenerates diagrams from changed code on PRs) and build-then-run builders (LangGraph-GUI). None of them combines bidirectional topology sync with drift-as-a-build-contract, and none is LangGraph-aware. The novelty is the combination, not any single capability.

No robust Python `stateDiagram-v2` parser exists today (pyStateGram is parse-only and incomplete; mermaid-parser-py needs Node.js and is pre-1.0), so lg2m must build and maintain its own parser + emitter covering `[else]`, `<<fork>>` / `<<join>>`, and composite states. That is a substantial, bug-prone piece (`parsing/mermaid.py`), and the space is moving, so the moat is partly time-sensitive.

The goal has been constant: link a Mermaid state diagram to LangGraph/LangChain code, detect drift both ways, scaffold either side, with 1:1 parity. The design took several passes: a decorator DSL that built the graph (rejected: lossy over LangGraph), then pure introspection (too far: dropped the annotations and demoted routing to unchecked prose). This plan is the resolution:

- **Introspection** stays the source of truth for graph *shape*.
- **Annotations** link code to the diagram and Markdown, and re-solve the lambda-doc case.
- **Routing is a generated, per-edge predicate model** (decided after research, see Section 3), which is the one routing representation that is 1:1 with *both* frameworks and cannot drift.

## 2. What the frameworks expose (designed against LangGraph 1.2.5 / langchain-core 1.4.7)

`get_graph()` is a method on `langchain_core`'s `Runnable`, so a LangGraph `CompiledStateGraph` and a LangChain LCEL chain / `RunnableBranch` both expose topology through the same call. The signatures are *not* identical: base `Runnable.get_graph(self, config=None)` has no `xray` parameter; only LangGraph's `Pregel` / `CompiledStateGraph` override adds `*, xray`, and only the LangGraph side expands subgraphs. Introspection still spans both frameworks, with that one asymmetry.

- `compiled.get_graph(config=None, *, xray: int | bool = False) -> Graph` (the LangGraph override; an `int` sets subgraph-expansion depth). `Graph.nodes: dict[str, Node]` (`Node = (id, name, data, metadata)`, `data` is the runnable, `None` for START/END). `Graph.edges: list[Edge]` (`Edge = (source, target, data, conditional: bool)`).
- **Conditional routing native shapes differ:** LangGraph is one opaque `path_fn` per source (`add_conditional_edges(source, path_fn, path_map)`), no built-in default, errors at runtime if the function returns a key not in `path_map`. LangChain `RunnableBranch` is a list of `(condition, target)` pairs plus a **mandatory** default. Neither exposes the per-branch condition logic to `get_graph()`; it is opaque in both.
- **State schema + reducers:** `compiled.builder.state_schema` + `typing.get_type_hints(..., include_extras=True)` yields types and `Annotated[T, reducer]`. Reducers (`add_messages`, `operator.add`, custom) are the merge rule for concurrent writes, so they are paired with parallel fan-out.
- **Parallel:** multiple unconditional out-edges run in parallel; `add_edge([a, b], c)` is a join. A `path_fn` returning a list routes to several targets; `Send(...)` is dynamic map-reduce (invisible to `get_graph()`). `Command(goto=...)` routes from inside a node and is invisible unless the node declares `add_node(..., destinations=...)`.
- **Subgraphs:** `get_graph(xray=True)` flattens a subgraph node; nested ids are `parent:child`.
- `draw_mermaid()` emits a flowchart only; lg2m keeps its own stateDiagram-v2 parser/emitter.
- Reaching the compiled object imports the module and runs the factory, so `check` runs user code up to (not including) invocation. Not execution-free.
- These surfaces are **semi-internal** (`compiled.builder.state_schema`, the `Node` / `Edge` NamedTuple shapes, `get_graph()` edge/label shapes, `xray` id formatting) and have churned across releases. lg2m targets a supported version *range*, not a single pin, keeps all framework-touching code behind the `[langgraph]` extra, and a CI matrix (Section 14) guards the range. The 1.2.5 / 1.4.7 versions are the *development* baseline, recent and movable, not load-bearing.

## 3. The routing model (the spine): per-edge predicates + generated router

**Decision (research-backed): Model A, generated.** A conditional fan-out is a list of per-edge named predicates plus a required `[else]` default. lg2m generates the actual routing function from that list. Rationale: LangGraph is natively one router function (Model B) and LangChain `RunnableBranch` is natively per-branch (Model A); only Model A compiles cleanly to *both* (a sequential `path_fn` for LangGraph, a 1:1 `RunnableBranch` for LangChain), and since neither framework can recover condition logic from a compiled object, the per-branch structure must be authored regardless, so author the portable one.

This portability is for *routing*, not the whole graph. Parallel fan-out with reducers, fan-in joins, `Send` map-reduce, `Command(goto)`, and subgraphs have no LCEL equivalent, so lg2m gives **full bidirectional fidelity for LangGraph** and only the **LCEL-expressible slice** (linear chains + `RunnableBranch`) for LangChain. The routing model is portable; the graph is not.

The model:

- Each leaf condition is a `@predicate("name")` function. The `and`/`or`/`not` lives inside its Python body (where the frameworks already keep it). There is no boolean-expression string anywhere.
- Routing predicates are **post-node** by lg2m convention: lg2m evaluates them on the state the source node produced, not its input. A LangGraph `path_fn` receives full state and *could* read fields the source node never wrote, so post-node evaluation is a constraint lg2m imposes, not a framework guarantee.
- A fan-out is declared as an ordered mapping `[(predicate, target), ..., (ELSE, target)]`. `[else]` is **required** (LangChain mandates a default; LangGraph errors on no-match; lg2m cannot prove exhaustiveness).
- lg2m **generates** the router from that mapping and **owns the `path_map`**: the generated `path_fn` returns the matched predicate's name (or the reserved `[else]` key), and `route.path_map` maps those keys to targets. The developer never hand-writes the `if/elif` selector, and never retypes the targets into `add_conditional_edges`. Because lg2m always passes an explicit, enumerable `path_map`, `get_graph()` never falls back to the overdraw-every-node edge it produces when `path_map` is omitted and the `path_fn` lacks a `Literal[...]` return hint. Keying the `path_map` by predicate name means `get_graph()` reports each conditional edge's label as its predicate name, so introspection validates labels, not just targets:

```python
@predicate("should_escalate")
def should_escalate(state) -> bool:                     # leaf condition (you write)
    return (is_urgent(state) or is_vip(state)) and not is_resolved(state)

route_after_classify = lg2m.router("classify_intent", [ # mapping (you declare)
    ("should_escalate",       "escalate_to_human"),
    ("should_canned_resolve", "auto_resolve"),
    (lg2m.ELSE,               "compose_reply"),          # required default
])                                                      # lg2m builds the selector

graph.add_conditional_edges("classify_intent", route_after_classify,
                            route_after_classify.path_map)  # lg2m owns the path_map
```

Because the diagram labels, the runtime router, and the `path_map` are all generated from the **same** mapping, they cannot drift; `get_graph()`'s conditional edges are predicate-labelled and agree with the mapping by construction, leaving the Markdown diagram as the only independently authored surface to reconcile. The only opaque code is each predicate body, and nothing claims what it does, so there is nothing for it to drift against. The same mapping also targets LangChain: lg2m can emit it as a `RunnableBranch` instead of a `path_fn`, which is the concrete 1:1-with-both guarantee.

In the diagram, each branch is a conditional transition labelled with its predicate, and the default uses the reserved `[else]` label:

```
classify_intent --> escalate_to_human: should_escalate
classify_intent --> auto_resolve:      should_canned_resolve
classify_intent --> compose_reply:     [else]
```

## 4. The three sources lg2m reconciles, and what it verifies

1. **Topology (introspection):** real nodes, edges, conditional flags, `path_map` targets, the state schema with reducers.
2. **Annotations:** `@node("id")`, `@predicate("name")`, `lg2m.router("source", [...])`, `@state_model` / `@data_model`. Decorators record metadata and return their target unchanged; `lg2m.router` returns a generated callable.
3. **The Markdown contract:** the topological diagram plus structured metadata and comments.

**Verified:** `@node` id == introspected node == diagram state; every routing predicate is a defined `@predicate`; the router mapping == introspected `path_map` **by construction** (lg2m generates both), and `get_graph()` reports each conditional edge's label as its predicate name, so introspection, the mapping, and the diagram conditional edges form a true three-way label+target check (if `get_graph()` and the mapping disagree, the router was not wired, or wired to the wrong source); every fan-out has an `[else]`; `@state_model` == introspected state; data model attributes / types / reducers vs the tables and metadata; prose linkage by id.

**Not verified:** a predicate's internal logic (opaque, and nothing claims it); `Command` / `Send` routes unless declared via `destinations`.

## 5. Architecture and package layout

Only the introspector imports `langgraph` / `langchain_core`. The annotated user code imports lg2m's light annotation + router module.

```
src/lg2m/
  __init__.py            # node, predicate, router, ELSE, state_model, data_model
  ir.py                  # GraphModel + Node/Edge/Predicate/Route/DataModel/Attribute/Meta/Diagnostic/SourceLocation
  annotations/
    decorators.py        # @node/@predicate/@state_model/@data_model (metadata only)
    router.py            # lg2m.router(source, branches) -> generated path_fn; also .as_runnable_branch() for LangChain
    registry.py          # per-import collection the annotations populate
    reader.py            # AST pass for file:line; merges with the runtime registry
  config/loader.py       # [tool.lg2m] / lg2m.toml -> graphs{id -> {graph: "mod:factory", markdown, sys_path, xray, framework}}
  discovery/resolve.py   # resolve entry point + markdown path
  introspect/
    base.py              # GraphIntrospector Protocol + FakeIntrospector
    langgraph_adapter.py # ONLY file importing the framework: get_graph() + state_schema -> topology IR
    loader.py            # import "mod:attr", run factory, surface import errors with location
  parsing/
    markdown.py          # frontmatter + sections + per-id prose + mermaid block + metadata (table/fence/note)
    mermaid.py           # stateDiagram-v2 parse/emit: states, transitions, [else], <<fork>>/<<join>>, composite states
    tables.py            # GFM tables (Data Models, Index, metadata tables)
    meta.py              # parse/emit the three metadata mechanisms (Section 7)
  diff/
    engine.py            # reconcile topology vs annotations vs diagram -> DriftReport
    categories.py        # DriftCategory + DiagnosticKind + hint templates
  report/                # model.py + text.py + json.py
  scaffold/
    from_doc.py          # markdown IR -> annotated code (@node/@predicate + lg2m.router + build_graph)
    from_code.py         # topology + annotations -> Markdown skeleton (labels from the router mapping)
    pyemit.py / mdemit.py / mermaid_emit.py
  cli.py                 # Typer: init, list, validate, check, gen
tests/
```

## 6. Intermediate Representation (`ir.py`)

- `SourceLocation(file, line, col?)`.
- `Node(id, kind: NODE|START|END, is_subgraph, anno_id?, prose?, docstring?, meta{}, loc?)`; identity = `id`.
- `Edge(src_id, dst_id, conditional: bool, predicate?, is_else: bool, parallel?, loc?)`; identity = `(src_id, dst_id, predicate)` (`predicate` is `None` for an unconditional edge), so two predicates routing to the same target are two distinct edges. For a conditional branch, `predicate` is its `@predicate` name; the default branch has `is_else=True`.
- `Predicate(name, prose?, docstring?, loc?)`; identity = `name`.
- `Route(source_id, branches: list[(predicate_name, target_id)], else_target, loc?)`; the ordered mapping lg2m generated the router from.
- `Attribute(name, type_str, reducer?, description?, loc?)`; `DataModel(name, style, is_graph_state, anno?, attributes[], prose?, loc?)`.
- `Meta(owner_id, kind: TABLE|FENCE|NOTE, data)`; the Markdown metadata attached to an entity.
- `Diagnostic(kind, subject, message, loc?)`: `Command`/`Send` without `destinations`, non-enumerable targets, import failure, missing `[else]`, router not wired (the compiled graph's `path_map` is absent or bound to a different source than the mapping declares).
- `GraphModel(graph_id, origin, nodes{}, edges[], predicates{}, routes{}, models{}, meta[], state_model_name?, diagnostics[])`.

## 7. Markdown contract

`# title` -> prose -> `## Index` (type in {node, edge, predicate}) -> `## Graph` (```mermaid stateDiagram-v2```) -> `## Data Models` -> `## Predicates` -> `## Nodes` -> `## Edges`. Frontmatter carries `lg2m_graph: <id>`.

lg2m emits `stateDiagram-v2`, not the `flowchart` dialect that LangGraph's `draw_mermaid` and Studio render. Flowcharts do have subgraphs and edge labels, so the divergence is justified only by the constructs they lack a first-class form for: `<<fork>>` / `<<join>>` pseudostates with join semantics for parallel fan-out / fan-in, composite states for subgraphs, and the `[*]` / `[else]` state-machine vocabulary that makes nesting and the default branch unambiguous. The accepted cost is losing alignment with Studio's native render and owning a `stateDiagram-v2` parser/emitter instead of reusing `draw_mermaid`.

**The diagram is purely topological.** Its vocabulary:

- Unconditional: `a --> b`. Conditional branch: `a --> b: predicate_name`. Default: `a --> c: [else]`.
- Parallel fan-out / fan-in: `<<fork>>` / `<<join>>` pseudostates, each declared with `state <id> <<fork>>` / `state <id> <<join>>` (the stereotype goes on the declaration line, not inline on a transition, so the emitted diagram is valid stock Mermaid that renders on GitHub/Obsidian).
  ```
  state fork_d <<fork>>
  state join_c <<join>>
  dispatch --> fork_d
  fork_d --> enrich
  fork_d --> score
  enrich --> join_c
  score  --> join_c
  join_c --> compose
  ```
- Subgraphs: composite states `state enrich { [*] --> lookup\n lookup --> [*] }`.

**Anything the diagram cannot draw lives in Markdown metadata**, in one of three forms (Q2 = all three; here are the inline examples):

1. Visible key/value table under the entity heading (drift-checked):
   ```markdown
   ### `dispatch`

   | meta | value |
   | --- | --- |
   | fan-out | parallel |
   | targets | enrich, score |
   ```
2. Hidden machine fence for facts that should not render (drift-checked):
   ```markdown
   ### `score`
   <!-- lg2m: reducer=operator.add; channel=running_total -->
   ```
3. Free-text note for what 1:1 cannot capture (human prose, not checked):
   ```markdown
   ### `map_items`

   > Note: fans out one `process_item` worker per item returned by `dispatch`;
   > the count is a runtime value, so the diagram shows one representative worker.
   ```

Reducers are shown in the Data Models type column (`Annotated[list, add_messages]`) and, where they govern a fan-out merge, restated as metadata on the joining node. When a node declares `add_node(..., destinations=...)`, its `Command(goto=...)` transitions are first-class introspected edges and are drawn as `Command`-kind (dashed) transitions in the diagram, like any other edge; the metadata then records only the *runtime* nuance (the goto fires from inside the node body). Without `destinations`, the `Command` route is invisible to introspection and survives only as a `> Note:`. `Send` declares its worker and dynamic width as metadata plus a `> Note:` for the runtime count, since its fan width is never a static value.

## 8. Diff categories (`diff/engine.py`)

- **Nodes** by id: `NODE_MISSING_IN_DOC` / `_IN_CODE`; `ANNOTATION_NODE_MISMATCH`; optional `PROSE_DRIFT`.
- **Edges** by `(src, dst, predicate)`: `EDGE_MISSING_*`; `EDGE_CONDITIONALITY_MISMATCH`; parallel fan-out is valid (modeled via fork), and multiple predicates to the same target are valid (distinct labelled edges), never an error.
- **Routing:** `ROUTE_TARGET_MISMATCH` (mapping vs diagram; the mapping and `path_map` are one generated source, so they cannot disagree); `ROUTER_NOT_WIRED` (`get_graph()` conditional edges absent or under a different source than the mapping declares); `PREDICATE_UNDEFINED`; `MISSING_ELSE`; `EDGE_LABEL_MISMATCH` (`get_graph()` edge label == mapping predicate name == diagram label, a true three-way check).
- **Predicates** by name: `PREDICATE_MISSING_*`.
- **Data models / reducers:** `MODEL_MISSING_*`, `ATTR_*`, `ATTR_TYPE_DRIFT`, `ATTR_REDUCER_DRIFT`, `STATE_MODEL_MISMATCH`.
- **Metadata:** `META_DRIFT` (a metadata fact disagrees with introspection, e.g. declared `targets` vs real fan-out).
- **Diagnostics:** non-enumerable conditional targets (warn and trust the diagram; `--strict` escalates), `Command`/`Send` without `destinations`, import failure.

Each `DriftItem` carries code and doc `file:line` plus a hint. `check` exits non-zero on any ERROR.

## 9. Worked example

`examples/support_pipeline/` (annotated, Model-A generated routing) is one connected graph that crosses every boundary in this plan once: a parallel enrichment fork/join, a generated conditional fan-out with a required `[else]`, an `investigate` subgraph, a `Send` map-reduce, a `Command(goto)` escalation, and three reducer kinds. Representative code:

```python
@node("classify_intent")
def classify_intent(state) -> dict: ...

@predicate("should_escalate")
def should_escalate(state) -> bool:
    f = state["flags"]
    return (f.get("urgent") or f.get("vip")) and not f.get("resolved")

route_after_classify = lg2m.router("classify_intent", [
    ("should_escalate",     "escalate_to_human"),
    ("should_auto_resolve", "auto_resolve"),
    (lg2m.ELSE,             "investigate"),       # required default
])
```

The diagram labels the conditional edges `should_escalate`, `should_auto_resolve`, `[else]`. A clean `lg2m check` reports nodes, predicates, routing, reducers, the subgraph, the parallel fork/join, metadata, and the diagram as OK. Renaming a target only in code yields `ROUTE_TARGET_MISMATCH` with both locations; deleting an `[else]` yields `MISSING_ELSE`. `examples/support_pipeline_native/` is the plain, un-annotated, runnable native version, rendered in both LangGraph (the full surface) and LangChain (the slice LCEL can express).

## 10. Scaffolding

- `lg2m gen --from-doc [--framework langgraph|langchain] [--model-style ...]`: from the Markdown, emit annotated code: `@state_model`/`@data_model`, `@node` stubs, a `@predicate` stub for every label in the diagram, a `lg2m.router(...)` mapping built from the conditional labels + `[else]`, and a complete `build_graph()`. Because Model A compiles to both frameworks, `--framework` selects a generated `path_fn` (LangGraph) or a `RunnableBranch` (LangChain).
- `lg2m gen --from-code`: introspect + read annotations + the router mapping, emit the Markdown skeleton (conditional labels from the mapping, metadata for non-topological facts, prose as TODO, existing prose preserved).

## 11. CLI (`cli.py`, Typer)

`init`, `list`, `validate` (each side parses; entry point imports; one state model; every fan-out has `[else]`), `check [--format text|json] [--strict] [--no-prose]`, `gen --from-doc | --from-code`. Exit `0` clean, `1` drift / structural error, `2` usage/config error.

## 12. Limitations (state in the README)

- A predicate's internal logic is never read; with Generate it never needs to be, because lg2m owns the selector and nothing claims what a predicate computes.
- `check` runs user code (import + build + compile) and the annotated code imports lg2m. Treat the target as untrusted; keep the lg2m runtime module import-light.
- `Command` / `Send` are invisible to introspection unless declared via `destinations`; `Send`'s dynamic fan width is a runtime value (metadata + `> Note:`, never a static count).
- Subgraphs are opaque unless `xray` is set, and `xray` rendering has a known upstream bug at 3+ nesting levels; lg2m documents and enforces a nesting-depth limit.
- Verification is **name-level** for both predicates and reducers (matched by `@predicate` name and by reducer object identity / `__name__`). A same-named, different-behavior swap of either passes silently.
- Post-node predicates are a **constraint lg2m imposes**, not a framework guarantee: a LangGraph `path_fn` sees full state and could read fields the source node never wrote.
- 1:1 fidelity is cleanest for **newly authored** graphs. Converting an existing hand-written `path_fn` with overlapping conditions into an ordered first-match Model A list is a real authoring step, not a mechanical 1:1.
- Prose *sync* (a write-back `lg2m sync` verb with a `.lg2m.lock` baseline-hash store, 3-way merge, and conflict policy, as sketched in the `support_pipeline` design note) is **out of scope for v1**: v1 only *reports* `PROSE_DRIFT`, it never writes prose back. That design note lives at the repo-level `docs/prose-sync.md`, kept out of `examples/` (which holds runnable artifacts).
- `gen` v1 regenerates the **topological core** faithfully (nodes, edges, conditional routers + `[else]`, parallel fan-out/in, the state model and its reducers), but does **not** reconstruct subgraphs, `Send`, or `Command` from the flattened canonical IR. `--from-code` emits canonical flat mermaid: a `parent:child` flattened-subgraph id cannot round-trip through mermaid (the `:` is mermaid's transition-label separator). `--from-doc` leaves a `# TODO` for any conditional edge without a router mapping (the Send/Command edges) and sanitises a `:`-id into a valid function name while preserving the `@node("parent:child")` string. Both directions round-trip **structurally** for subgraph-free graphs (the round-trip goldens use a minimal fixture; the rich example is covered by a lenient smoke). De-canonicalising subgraph/`Send`/`Command` back into diagram sugar is a future layer.

## 13. Build order

1. `ir.py` + `config/loader.py` + `parsing/{mermaid,markdown,tables,meta}.py` (no framework import).
2. `annotations/{decorators,router,registry,reader}.py` + `introspect/{base,Fake}` , then `diff/engine.py` + `report/*`: reconciliation works against a FakeIntrospector + a fixture registry.
3. `introspect/langgraph_adapter.py` + `loader.py` behind the `[langgraph]` extra; `@pytest.mark.langgraph` suite.
4. `cli.py`.
5. `scaffold/*` and `gen` (both `--framework` targets); round-trip goldens.

## 14. Test strategy (pytest + ruff)

- **Router generation:** `lg2m.router` builds a `path_fn` whose behavior equals first-match-then-`[else]` and returns the matched predicate's name; `route.path_map` is keyed by predicate name (with `[else]` reserved) so two predicates to one target yield two labelled edges; the same mapping emits an equivalent `RunnableBranch`; missing `[else]` and a predicate named `[else]` are rejected.
- **Annotation reader / AST:** ids, file:line, the router mapping recovered.
- **Introspector** (`@pytest.mark.langgraph`): chain, parallel fan-out + join, conditional with/without `path_map`, `Command`/`Send`, subgraph, reducers; the right topology IR and diagnostics.
- **Diff + metadata:** one fixture per category, including `ROUTE_TARGET_MISMATCH`, `MISSING_ELSE`, `META_DRIFT`, and the parallel-fork case that must not error.
- **Golden round-trips:** code -> markdown -> IR and markdown -> generated code -> introspect -> IR equality on structural fields.
- **End-to-end:** the `support_pipeline` fixture checks clean; a routing-drifted copy returns non-zero; both `gen` directions round-trip.
- **CLI:** `CliRunner` exit codes; `check` writes nothing.
- **Version matrix:** run the `@pytest.mark.langgraph` suite across a supported range of LangGraph / langchain-core versions in CI (not just the pinned 1.2.5 / 1.4.7), so an upstream `Node` / `Edge` shape or `get_graph()` change surfaces as a test failure, not a user bug report.
