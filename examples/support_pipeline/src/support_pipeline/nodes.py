"""Node functions for support_pipeline, with lg2m @node linking annotations.

`@node("id")` links each function to its state in the diagram and to its
`### id` prose in docs/support_pipeline.md. It records metadata and returns the
function unchanged; you still register the node natively in graph.py with
`add_node("id", fn)`. lg2m checks that the @node id matches the add_node name in
the introspected graph and the node in the diagram, or it reports drift.

The investigate subgraph's own nodes (gather_logs, analyze) also carry @node ids;
with xray=True lg2m sees them as `investigate:gather_logs` / `investigate:analyze`
and reconciles them against the composite state in the diagram.
"""

from langgraph.types import Command

from lg2m import node

from .state import PipelineState, Ticket


# --- Top-level nodes ---------------------------------------------------------

@node("ingest_ticket")
def ingest_ticket(state: PipelineState) -> dict:
    raw = state.get("ticket")
    ticket = raw if isinstance(raw, Ticket) else Ticket(**dict(raw or {}))
    body = ticket.body.lower()
    # Derive the work items the investigate path will map over.
    signals = [tok for tok in ("login", "billing", "timeout", "crash", "data")
               if tok in body]
    return {
        "ticket": ticket,
        "items": signals or ["general"],
        "messages": [{"role": "system", "content": f"ingested: {ticket.subject}"}],
        "attempts": 1,
    }


@node("fetch_history")
def fetch_history(state: PipelineState) -> dict:
    # Parallel branch A. Writes the shared `enrichment` channel (operator.add).
    return {"enrichment": [f"history: 2 prior tickets for {state['ticket'].subject}"]}


@node("lookup_account")
def lookup_account(state: PipelineState) -> dict:
    # Parallel branch B. Also writes `enrichment`; operator.add merges the two
    # concurrent writes into one list.
    tier = state["ticket"].customer_tier
    return {"enrichment": [f"account: tier={tier}"]}


@node("classify_intent")
def classify_intent(state: PipelineState) -> dict:
    # Fan-in point of the parallel enrichment, and the conditional source.
    ticket = state["ticket"]
    body = ticket.body.lower()
    flags = {
        "urgent": ticket.priority == "high" or "asap" in body,
        "vip": ticket.customer_tier == "enterprise",
        "resolved": "already solved" in body or "resolved" in body,
        "has_attachment": "attachment" in body or "see attached" in body,
    }
    return {"flags": flags, "messages": [{"role": "system", "content": "classified"}]}


@node("auto_resolve")
def auto_resolve(state: PipelineState) -> dict:
    return {
        "resolution": "canned: applied known answer for already-resolved ticket",
        "attempts": 1,
    }


@node("escalate_to_human")
def escalate_to_human(state: PipelineState) -> Command:
    """Command node: routes from inside the body with Command(goto=...).

    Invisible to get_graph() unless the node declares its destinations; graph.py
    declares ("compose_reply",) so the edge is part of the introspected topology.
    The goto target is chosen here, not by an out-edge. The diagram cannot draw a
    goto, so the destination is restated as metadata under `### escalate_to_human`.
    """
    return Command(
        goto="compose_reply",
        update={
            "resolution": "escalated: handed off to human agent queue",
            "messages": [{"role": "system", "content": "handoff -> human queue"}],
            "attempts": 1,
        },
    )


@node("map_items")
def map_items(state: PipelineState) -> dict:
    # Prepares the fan-out; the actual Send list is built by fan_out_items.
    return {"messages": [{"role": "system",
                          "content": f"mapping {len(state['items'])} item(s)"}]}


@node("process_item")
def process_item(state: dict) -> dict:
    # One Send worker per item. Writes item_results, merged by extend_unique.
    item = state["item"]
    return {"item_results": [f"analyzed:{item}"]}


@node("reduce_items")
def reduce_items(state: PipelineState) -> dict:
    # Join after the dynamic Send fan-out completes.
    found = ", ".join(sorted(state.get("item_results", [])))
    return {"resolution": f"investigated: {found}", "attempts": 1}


@node("compose_reply")
def compose_reply(state: PipelineState) -> dict:
    resolution = state.get("resolution", "")
    reply = f"Re: {state['ticket'].subject} -- {resolution}"
    return {"messages": [{"role": "assistant", "content": reply}]}


# --- Subgraph nodes: investigate ---------------------------------------------

@node("gather_logs")
def gather_logs(state: PipelineState) -> dict:
    return {"messages": [{"role": "system",
                          "content": f"gathered logs for {len(state['items'])} signal(s)"}]}


@node("analyze")
def analyze(state: PipelineState) -> dict:
    return {"messages": [{"role": "system", "content": "analyzed logs"}]}
