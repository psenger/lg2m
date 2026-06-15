"""State and payload models for support_pipeline, with lg2m linking annotations.

The decorators below are lg2m annotations. They record metadata and return the
class unchanged, so they do not affect LangGraph at run time. lg2m reads them to
link each model to its `### Model` prose in docs/support_pipeline.md, and confirms
the graph-state model matches the introspected `builder.state_schema`. Types and
reducers are still read from the real schema by introspection; this file also
defines the custom `extend_unique` reducer the Send workers merge through.
"""

import operator
from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel

from lg2m import data_model, state_model


# --- Custom reducer ----------------------------------------------------------

def extend_unique(left: list | None, right: list | None) -> list:
    """Custom channel reducer: append the right writes, dropping duplicates.

    The third reducer kind, neither add_messages nor operator.add. The Send
    workers write item_results concurrently; this merges them while keeping the
    list free of repeats. lg2m reports it as the reducer on the item_results
    channel and pairs it with the Send fan-in.
    """
    out = list(left or [])
    for item in right or []:
        if item not in out:
            out.append(item)
    return out


# --- Data model --------------------------------------------------------------

@data_model
class Ticket(BaseModel):
    subject: str
    body: str
    priority: str          # 'low' | 'normal' | 'high'
    customer_tier: str     # 'free' | 'pro' | 'enterprise'


# --- Graph state -------------------------------------------------------------

@state_model
class PipelineState(TypedDict):
    ticket: Ticket
    messages: Annotated[list, add_messages]        # reducer: add_messages
    attempts: Annotated[int, operator.add]         # reducer: operator.add
    enrichment: Annotated[list, operator.add]      # reducer: operator.add (parallel merge)
    flags: dict
    items: list
    item_results: Annotated[list, extend_unique]   # reducer: custom (Send merge)
    resolution: str
