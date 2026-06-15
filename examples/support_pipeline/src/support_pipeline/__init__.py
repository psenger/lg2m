"""support_pipeline: native LangGraph + lg2m annotations (Model-A routing).

The graph is ordinary LangGraph (graph.py builds it with add_node / add_edge /
add_conditional_edges). On top of that, the functions carry lg2m annotations
that link them to the diagram and markdown:

  @node                links a node function to its diagram state and `### id` prose
  @predicate           marks a WHOLE leaf condition (its and/or/not lives in the
                       body); a fan-out lists predicates, not boolean strings
  lg2m.router          declares the ordered (predicate, target) mapping plus the
                       required lg2m.ELSE default; lg2m GENERATES the selector
  @state_model / @data_model  link the models to their `### Model` prose

`lg2m check` introspects the real compiled graph for topology, then reconciles it
with these annotations and the diagram. The decorators record metadata and return
the wrapped object unchanged, so they do not alter run-time behavior.
"""

from .graph import build_graph

__all__ = ["build_graph"]
