"""The LangGraph introspection adapter — the framework-coupled seam (docs/design.md Sections 2, 5).

Translates a compiled LangGraph graph into the canonical ``ir.GraphModel(origin="code")`` the
diff core already compares against (the exact shape the layer-2b Fake authors). It reads the real
topology via ``compiled.get_graph(xray=True)`` and the state schema via
``compiled.builder.state_schema``.

``get_graph(xray=True)`` already yields canonical vocabulary — flattened ``parent:child`` subgraph
nodes, ``__start__`` / ``__end__`` sentinels, plain parallel edges, and conditional edges whose
``.data`` is the ``path_map`` key (the ``@predicate`` name for a Model-A graph). So no
canonicalization runs on the code side.

It is **framework-coupled** (only meaningful with a real compiled graph) but reads it by
duck-typing, so it imports no framework symbol; it is still not imported by
``introspect/__init__.py`` (nothing pulls it in until ``pipeline.check()`` asks for it).
"""

from __future__ import annotations

from typing import Any

from lg2m.annotations.registry import Registry, get_registry
from lg2m.introspect.schema import model_from_class
from lg2m.ir import ELSE_LABEL, Edge, GraphModel, Node, NodeKind

START_ID = "__start__"
END_ID = "__end__"


class LangGraphIntrospector:
    """``GraphIntrospector`` over a compiled LangGraph graph."""

    def __init__(
        self, compiled: Any, *, xray: bool = True, registry: Registry | None = None
    ) -> None:
        self._compiled = compiled
        self._xray = xray
        self._registry = registry if registry is not None else get_registry()

    def introspect(self, graph_id: str) -> GraphModel:
        g = self._compiled.get_graph(xray=self._xray)
        gm = GraphModel(graph_id=graph_id, origin="code")
        for node_id in g.nodes:
            gm.nodes[node_id] = Node(id=node_id, kind=_kind(node_id))
        for edge in g.edges:
            gm.edges.append(_edge(edge))
        self._add_models(gm)
        return gm

    def _add_models(self, gm: GraphModel) -> None:
        builder = getattr(self._compiled, "builder", None)
        schema = getattr(builder, "state_schema", None) or getattr(builder, "schema", None)
        if schema is not None:
            dm = model_from_class(schema, is_graph_state=True)
            gm.models[dm.name] = dm
            gm.state_model_name = dm.name
        for entry in self._registry.models.values():
            if entry.is_graph_state:
                continue  # the graph state comes from the compiled schema above
            dm = model_from_class(entry.target, is_graph_state=False)
            gm.models.setdefault(dm.name, dm)


def _kind(node_id: str) -> NodeKind:
    if node_id == START_ID:
        return NodeKind.START
    if node_id == END_ID:
        return NodeKind.END
    return NodeKind.NODE


def _edge(edge: Any) -> Edge:
    data = getattr(edge, "data", None)
    conditional = bool(edge.conditional)
    predicate = str(data) if (conditional and data) else None
    return Edge(
        src_id=edge.source,
        dst_id=edge.target,
        predicate=predicate,
        conditional=conditional,
        is_else=(predicate == ELSE_LABEL),
    )
