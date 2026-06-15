"""GraphIntrospector port + framework-free FakeIntrospector (docs/design.md Sections 4, 5).

The introspector is the only seam that, in a later layer, reads the real compiled
graph via ``get_graph(xray=True)``. Its output is "topology IR": an ``ir.GraphModel``
with ``origin="code"`` whose node ids are already in canonical (topology)
vocabulary — plain parallel edges instead of ``<<fork>>`` / ``<<join>>``, flattened
``parent:child`` subgraph nodes instead of a composite state, and ``__start__`` /
``__end__`` sentinels instead of ``[*]``.

Layer 2b ships only the Fake. The real ``langgraph_adapter`` (which imports the
framework, behind the ``[langgraph]`` extra) is a later layer and MUST NOT be
imported from here, or importing ``lg2m.introspect`` would import langgraph. Both
adapters satisfy this one Protocol and return the same canonical shape, so an
engine test written against the Fake holds for the real adapter.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lg2m.ir import GraphModel


@runtime_checkable
class GraphIntrospector(Protocol):
    """Port owned by the diff core; the domain language is the IR, not the framework."""

    def introspect(self, graph_id: str) -> GraphModel:
        """Return a code-side ``GraphModel(origin="code")`` in canonical vocabulary."""
        ...


class FakeIntrospector:
    """Value-backed ``GraphIntrospector``: returns a pre-authored ``GraphModel``.

    The stand-in for the real adapter in framework-free tests. Author the model in
    canonical / topology vocabulary so it lines up with the canonicalized diagram.
    """

    def __init__(self, model: GraphModel) -> None:
        self._model = model

    def introspect(self, graph_id: str) -> GraphModel:
        return self._model
