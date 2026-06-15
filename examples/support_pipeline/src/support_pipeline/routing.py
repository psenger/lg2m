"""Routing for support_pipeline: the generated router and the Send fan-out.

Two routing constructs live here.

  lg2m.router("classify_intent", [...])  declares the ordered fan-out as a
      mapping of (predicate, target) pairs ending in the required lg2m.ELSE
      default. lg2m GENERATES the selector from this mapping AND owns the path_map
      (keyed by predicate name), so you never hand-write the if / elif and never
      retype the targets into add_conditional_edges. Because the diagram labels,
      the runtime router, and the path_map all come from the SAME mapping, they
      cannot drift. lg2m checks that:
        - every predicate name is a defined @predicate,
        - get_graph()'s conditional-edge labels equal the predicate names; the
          mapping and the path_map agree by construction, so this is a true
          three-way label+target check against the diagram,
        - an lg2m.ELSE default is present.

  fan_out_items(state)  is the native Send map-reduce. lg2m does not own Send; the
      worker target (process_item) and the dynamic width are declared to
      introspection via the conditional edge in graph.py and restated as Markdown
      metadata plus a `> Note:` under `### map_items`. The fan width is a runtime
      value, never a static count.
"""

import lg2m
from langgraph.types import Send

from .state import PipelineState


# Conditional fan-out after classify_intent. lg2m.router builds the path_fn from
# this mapping; lg2m.ELSE is the required no-match default (investigate).
route_after_classify = lg2m.router("classify_intent", [
    ("should_escalate",     "escalate_to_human"),
    ("should_auto_resolve", "auto_resolve"),
    (lg2m.ELSE,             "investigate"),
])


def fan_out_items(state: PipelineState) -> list:
    """Return one Send per work item: dynamic width, decided at runtime.

    Native LangGraph map-reduce; lg2m records the worker + dynamic width as
    metadata, it does not generate this.
    """
    return [Send("process_item", {"item": item}) for item in state["items"]]
