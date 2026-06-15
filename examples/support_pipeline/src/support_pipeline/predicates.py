"""Leaf predicates for support_pipeline (Model-A routing).

`@predicate("name")` marks a function as a WHOLE leaf condition for the
conditional fan-out out of classify_intent. The and / or / not lives inside the
Python body, where LangGraph already keeps it; there is no boolean-expression
string anywhere. The router mapping in routing.py references each predicate by
name, and the diagram labels the matching conditional edge with that same name.

lg2m checks that every predicate referenced by the router is defined here and
links each to its `### name` prose in docs/support_pipeline.md. It does not read
the body (the logic is opaque, and nothing claims what it computes), so a
predicate's internals never drift against anything.
"""

from lg2m import predicate

from .state import PipelineState


@predicate("should_escalate")
def should_escalate(state: PipelineState) -> bool:
    f = state["flags"]
    return (f.get("urgent") or f.get("vip")) and not f.get("resolved")


@predicate("should_auto_resolve")
def should_auto_resolve(state: PipelineState) -> bool:
    f = state["flags"]
    return bool(f.get("resolved")) and not f.get("has_attachment")
