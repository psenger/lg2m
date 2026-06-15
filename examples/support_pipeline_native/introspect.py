"""introspect.py: print the topology lg2m would read from the compiled graph.

lg2m never re-implements LangGraph's wiring; it imports the factory, compiles it,
and calls `compiled.get_graph()` for the real nodes/edges/conditional flags, plus
the state schema (types + reducers). This script dumps exactly that, so you can
see the "topology truth" the lg2m introspector reconciles against the diagram.

Run:  python introspect.py

It prints, for the support_pipeline graph:
  - nodes (with the subgraph flattened by xray=True -> investigate:gather_logs ...)
  - edges with their `conditional` flag
  - the state schema with each channel's reducer

Note the boundaries that are visible vs invisible to introspection:
  - parallel fork/join shows up as plain multi-edges (no pseudostate; lg2m draws
    the <<fork>>/<<join>> from the fan-out shape)
  - the Command(goto) edge IS visible because escalate_to_human declares
    destinations=("compose_reply",)
  - the Send fan-out shows as a conditional edge map_items -> process_item; the
    dynamic width is a runtime value and never appears here
"""

import operator
import typing

from langgraph.graph.message import add_messages

from langgraph_app import PipelineState, build_graph, extend_unique

_REDUCER_NAMES = {
    add_messages: "add_messages",
    operator.add: "operator.add",
    extend_unique: "extend_unique (custom)",
}


def _reducer_label(meta) -> str:
    # Annotated[T, reducer] surfaces the reducer in __metadata__.
    extras = getattr(meta, "__metadata__", ())
    for extra in extras:
        if extra in _REDUCER_NAMES:
            return _REDUCER_NAMES[extra]
        if callable(extra):
            return getattr(extra, "__name__", repr(extra))
    return "-"


def dump_topology() -> None:
    app = build_graph()
    g = app.get_graph(xray=True)

    print("=== NODES (xray=True flattens the investigate subgraph) ===")
    for node_id in g.nodes:
        print(f"  {node_id}")

    print("\n=== EDGES (conditional flag from get_graph) ===")
    for e in g.edges:
        kind = "conditional" if e.conditional else "unconditional"
        label = f"  [{e.data}]" if getattr(e, "data", None) else ""
        print(f"  {e.source:>22} -> {e.target:<22} ({kind}){label}")

    print("\n=== STATE SCHEMA + REDUCERS ===")
    hints = typing.get_type_hints(PipelineState, include_extras=True)
    for name, hint in hints.items():
        origin = typing.get_args(hint)
        base = origin[0] if origin else hint
        base_name = getattr(base, "__name__", str(base))
        print(f"  {name:<14} {base_name:<10} reducer={_reducer_label(hint)}")


if __name__ == "__main__":
    dump_topology()
