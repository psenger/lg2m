# Example: support_pipeline (lg2m annotations + introspection)

A mock of a project that uses lg2m. The code under `src/` is native LangGraph
**plus lg2m annotations** that link each function to the diagram and markdown,
name the leaf conditions, and declare the conditional fan-out as a generated
router. lg2m is not built yet, so the `lg2m ...` transcript below is an
illustrative mock.

Contrast with `examples/support_pipeline_native`: the same graph with no
annotations and no lg2m dependency (that one is runnable today). This one imports
lg2m for the decorators and `lg2m.router`, so it is illustrative until the tool
exists.

This example exercises the full surface of the design: a chain in, a parallel
fork/join with a reducer-governed merge, a generated conditional fan-out with a
required `[else]` default, a subgraph, a dynamic `Send` map-reduce, a
`Command(goto)` node, and all three reducer kinds.

## The annotations

The conditional fan-out uses the Model-A design: each leaf condition is a whole
`@predicate` (its `and` / `or` / `not` lives in the body, never in a string), and
the fan-out is an ordered `(predicate, target)` mapping ending in the required
`lg2m.ELSE` default. lg2m **generates** the selector from that mapping; you never
hand-write the `if` / `elif`.

```python
@node("classify_intent")               # links a function to a diagram state + its ### prose
def classify_intent(state): ...

@predicate("should_escalate")          # a WHOLE leaf condition; the and/or/not is in the body
def should_escalate(state) -> bool:
    f = state["flags"]
    return (f.get("urgent") or f.get("vip")) and not f.get("resolved")

# the fan-out as an ordered mapping; lg2m builds the router from it
route_after_classify = lg2m.router("classify_intent", [
    ("should_escalate",     "escalate_to_human"),
    ("should_auto_resolve", "auto_resolve"),
    (lg2m.ELSE,             "investigate"),     # required default
])

@state_model / @data_model             # link the models to their ### Model prose
```

The decorators record metadata and return the wrapped object unchanged, so the
graph still runs as plain LangGraph. You still write `add_node` / `add_edge` /
`add_conditional_edges` yourself in `graph.py`, and `route_after_classify` (the
callable lg2m generated) is passed to `add_conditional_edges` like any path_fn.

## How lg2m uses topology AND annotations

`lg2m check` imports `support_pipeline.graph:build_graph`, compiles it, reads
`compiled.get_graph(xray=True)` for the real topology, then reconciles three
sources:

- **topology** (introspection): the real nodes (with the investigate subgraph
  flattened by xray), edges, conditional flags, the `path_map` targets of
  classify_intent, and the state schema with its reducers.
- **annotations** (`@node` / `@predicate` / `lg2m.router` / `@state_model` /
  `@data_model`): the intended links and the ordered router mapping.
- **the diagram + tables + metadata** in `docs/support_pipeline.md`.

Because the router mapping generates both the runtime selector and the diagram
labels, routing cannot drift; the only opaque code is each predicate body, and
nothing claims what it does. Boundaries the diagram cannot draw (the parallel
merge reducer, the `Command` destination, the `Send` worker and its runtime
width) live as Markdown metadata, in all three forms: a visible key/value table,
a hidden machine fence, and a free-text `> Note:`.

```text
$ lg2m check
graph: support_pipeline  (support_pipeline.graph:build_graph -> CompiledStateGraph)
  introspected: 11 nodes, 15 edges (5 conditional), state PipelineState (8 fields)

  nodes .......... 11/11  OK   (@node ids == graph nodes == diagram states)
  edges .......... 15/15  OK
  conditionality . OK         (5 conditional: 3 classify branches + map_items Send + escalate Command)
  predicates ..... 2/2    OK   (should_escalate, should_auto_resolve)
  routing ........ OK         (router mapping == path_map (generated) == get_graph labels == diagram; [else] -> investigate present)
  parallel ....... OK         (ingest_ticket fork -> {fetch_history, lookup_account} join -> classify_intent)
  subgraph ....... OK         (investigate: gather_logs -> analyze, flattened by xray)
  data models .... 2/2    OK   (@state_model PipelineState == introspected state; Ticket)
  reducers ....... 4/4    OK   (add_messages, operator.add x2, extend_unique)
  metadata ....... OK         (fan-out table, enrichment + Command fences, Send note)
  diagram ........ OK
  diagnostics .... none

0 drift items. exit 0
```

## Layout

```
examples/support_pipeline/
  lg2m.toml                    # graph = "support_pipeline.graph:build_graph"; markdown = "docs/..."; xray = true
  docs/support_pipeline.md     # the contract: topological diagram + Predicates + Data Models + per-node metadata
  src/support_pipeline/
    state.py       # @state_model PipelineState, @data_model Ticket, the extend_unique custom reducer
    nodes.py       # @node functions (top-level nodes + the investigate subgraph nodes)
    predicates.py  # @predicate should_escalate, should_auto_resolve (whole leaf conditions)
    routing.py     # lg2m.router mapping (generated router) + the Send fan_out_items
    graph.py       # native build_graph() wiring, the subgraph, the Command node, the Send edge
    __init__.py
```

## Caveats

- The `lg2m ...` transcript is a mock; the tool is not built yet.
- Unlike `support_pipeline_native`, this code imports `lg2m` for the decorators
  and `lg2m.router`, so it will not import or run until the lg2m package exists.
- The decorators are metadata-only: they record linking information and return
  their target unchanged, so they do not change the graph's behavior.
