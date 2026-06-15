"""support_pipeline_native (LangGraph): the comprehensive, runnable native graph.

This is the "before lg2m" picture for the FULL surface of the lg2m design. It is
ordinary LangGraph 1.2.5 with no lg2m: no decorators, no registry, no Markdown
contract. Its companion `langchain_app.py` renders the slice LangChain can
express; `examples/support_pipeline/` is the same graph with lg2m applied.

One connected graph, every boundary the plan names appears exactly once:

  - chain edges ............... START -> ingest_ticket -> ... -> END
  - parallel fork/fan-in ..... ingest_ticket fans out to fetch_history +
                               lookup_account, which fan back in to classify_intent
  - reducer-governed merge ... the two parallel branches both write `enrichment`,
                               merged by operator.add (concurrent writes)
  - conditional routing ...... classify_intent -> {escalate, auto_resolve, investigate}
  - required [else] default .. the investigate branch is the no-match default
  - subgraph ................. `investigate` is a compiled sub-StateGraph
                               (gather_logs -> analyze), flattened by xray=True
  - Send map-reduce .......... map_items fans out one process_item per work item
                               via Send(...) (dynamic width), reduce_items joins
  - Command(goto) ............ escalate_to_human routes from inside the node body
                               with Command(goto=...), declared via destinations=
  - three reducer kinds ...... add_messages (messages), operator.add (attempts,
                               enrichment), and a custom reducer (item_results)

Node bodies are deterministic stand-ins (no LLM, no API keys) so the run is
reproducible. `python langgraph_app.py` drives one ticket down each of the three
branches and prints the result of each.
"""

import operator
from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, Send
from pydantic import BaseModel


# --- Data models -------------------------------------------------------------

class Ticket(BaseModel):
    subject: str
    body: str
    priority: str          # 'low' | 'normal' | 'high'
    customer_tier: str     # 'free' | 'pro' | 'enterprise'


# --- Custom reducer ----------------------------------------------------------

def extend_unique(left: list | None, right: list | None) -> list:
    """Custom channel reducer: append the right writes, dropping duplicates.

    Demonstrates the third reducer kind (neither add_messages nor operator.add).
    The Send workers write item_results concurrently; this merges them while
    keeping the list free of repeats.
    """
    out = list(left or [])
    for item in right or []:
        if item not in out:
            out.append(item)
    return out


# --- Graph state -------------------------------------------------------------

class PipelineState(TypedDict):
    ticket: Ticket
    messages: Annotated[list, add_messages]        # reducer: add_messages
    attempts: Annotated[int, operator.add]         # reducer: operator.add
    enrichment: Annotated[list, operator.add]      # reducer: operator.add (parallel merge)
    flags: dict
    items: list
    item_results: Annotated[list, extend_unique]   # reducer: custom (Send merge)
    resolution: str


# --- Top-level nodes ---------------------------------------------------------

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


def fetch_history(state: PipelineState) -> dict:
    # Parallel branch A. Writes the shared `enrichment` channel (operator.add).
    return {"enrichment": [f"history: 2 prior tickets for {state['ticket'].subject}"]}


def lookup_account(state: PipelineState) -> dict:
    # Parallel branch B. Also writes `enrichment`; operator.add merges the two
    # concurrent writes into one list.
    tier = state["ticket"].customer_tier
    return {"enrichment": [f"account: tier={tier}"]}


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


def auto_resolve(state: PipelineState) -> dict:
    return {
        "resolution": "canned: applied known answer for already-resolved ticket",
        "attempts": 1,
    }


def escalate_to_human(state: PipelineState) -> Command:
    """Command node: routes from inside the body with Command(goto=...).

    Invisible to get_graph() unless the node declares its destinations; we declare
    ("compose_reply",) in build_graph so the edge is part of the introspected
    topology. The goto target is chosen here, not by an out-edge.
    """
    return Command(
        goto="compose_reply",
        update={
            "resolution": "escalated: handed off to human agent queue",
            "messages": [{"role": "system", "content": "handoff -> human queue"}],
            "attempts": 1,
        },
    )


def map_items(state: PipelineState) -> dict:
    # Prepares the fan-out; the actual Send list is built by fan_out_items below.
    return {"messages": [{"role": "system",
                          "content": f"mapping {len(state['items'])} item(s)"}]}


def process_item(state: dict) -> dict:
    # One Send worker per item. Writes item_results, merged by extend_unique.
    item = state["item"]
    return {"item_results": [f"analyzed:{item}"]}


def reduce_items(state: PipelineState) -> dict:
    # Join after the dynamic Send fan-out completes.
    found = ", ".join(sorted(state.get("item_results", [])))
    return {"resolution": f"investigated: {found}", "attempts": 1}


def compose_reply(state: PipelineState) -> dict:
    resolution = state.get("resolution", "")
    reply = f"Re: {state['ticket'].subject} -- {resolution}"
    return {"messages": [{"role": "assistant", "content": reply}]}


# --- Conditional routing (post-classify) -------------------------------------
# These are the leaf predicates lg2m's Model A would name with @predicate.

def should_escalate(state: PipelineState) -> bool:
    f = state["flags"]
    return (f.get("urgent") or f.get("vip")) and not f.get("resolved")


def should_auto_resolve(state: PipelineState) -> bool:
    f = state["flags"]
    return bool(f.get("resolved")) and not f.get("has_attachment")


def route_after_classify(state: PipelineState) -> str:
    """First-match, then [else]. lg2m would GENERATE this from the router mapping;
    here it is hand-written (the maintenance burden lg2m removes)."""
    if should_escalate(state):
        return "escalate_to_human"
    if should_auto_resolve(state):
        return "auto_resolve"
    return "investigate"          # [else] default


# --- Send fan-out (dynamic map-reduce) ---------------------------------------

def fan_out_items(state: PipelineState) -> list:
    """Return one Send per work item: dynamic width, decided at runtime."""
    return [Send("process_item", {"item": item}) for item in state["items"]]


# --- Subgraph: investigate ---------------------------------------------------

class InvestigateState(TypedDict):
    ticket: Ticket
    items: list
    messages: Annotated[list, add_messages]


def gather_logs(state: InvestigateState) -> dict:
    return {"messages": [{"role": "system",
                          "content": f"gathered logs for {len(state['items'])} signal(s)"}]}


def analyze(state: InvestigateState) -> dict:
    return {"messages": [{"role": "system", "content": "analyzed logs"}]}


def build_investigate_subgraph():
    sub = StateGraph(InvestigateState)
    sub.add_node("gather_logs", gather_logs)
    sub.add_node("analyze", analyze)
    sub.add_edge(START, "gather_logs")
    sub.add_edge("gather_logs", "analyze")
    sub.add_edge("analyze", END)
    return sub.compile()


# --- Graph assembly ----------------------------------------------------------

def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("ingest_ticket", ingest_ticket)
    graph.add_node("fetch_history", fetch_history)
    graph.add_node("lookup_account", lookup_account)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("auto_resolve", auto_resolve)
    # Command node: declare destinations so the goto edge is introspectable.
    graph.add_node("escalate_to_human", escalate_to_human,
                   destinations=("compose_reply",))
    graph.add_node("investigate", build_investigate_subgraph())   # subgraph as a node
    graph.add_node("map_items", map_items)
    graph.add_node("process_item", process_item)
    graph.add_node("reduce_items", reduce_items)
    graph.add_node("compose_reply", compose_reply)

    # chain in
    graph.add_edge(START, "ingest_ticket")

    # parallel fork: ingest -> {fetch_history, lookup_account}
    graph.add_edge("ingest_ticket", "fetch_history")
    graph.add_edge("ingest_ticket", "lookup_account")
    # parallel fan-in (join): both -> classify_intent (runs once, after both)
    graph.add_edge("fetch_history", "classify_intent")
    graph.add_edge("lookup_account", "classify_intent")

    # conditional fan-out with required [else] = investigate
    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "escalate_to_human": "escalate_to_human",
            "auto_resolve": "auto_resolve",
            "investigate": "investigate",
        },
    )

    # subgraph -> map_items -> (Send) process_item -> reduce_items -> compose
    graph.add_edge("investigate", "map_items")
    graph.add_conditional_edges("map_items", fan_out_items, ["process_item"])
    graph.add_edge("process_item", "reduce_items")
    graph.add_edge("reduce_items", "compose_reply")

    # the other two branches converge on compose_reply
    graph.add_edge("auto_resolve", "compose_reply")
    # escalate_to_human reaches compose_reply via Command(goto), not an edge.

    graph.add_edge("compose_reply", END)

    return graph.compile()


# --- Demo --------------------------------------------------------------------

_TICKETS = {
    "escalate (Command path)": Ticket(
        subject="Cannot log in",
        body="urgent asap, production down",
        priority="high",
        customer_tier="enterprise",
    ),
    "auto_resolve path": Ticket(
        subject="How do I export?",
        body="already solved in your docs, just confirming",
        priority="low",
        customer_tier="free",
    ),
    "investigate (subgraph + Send) path": Ticket(
        subject="Intermittent errors",
        body="login times out and billing crash on submit",
        priority="normal",
        customer_tier="pro",
    ),
}


def _run_one(app, ticket: Ticket) -> dict:
    return app.invoke({
        "ticket": ticket,
        "messages": [],
        "attempts": 0,
        "enrichment": [],
        "flags": {},
        "items": [],
        "item_results": [],
        "resolution": "",
    })


if __name__ == "__main__":
    app = build_graph()
    for label, ticket in _TICKETS.items():
        result = _run_one(app, ticket)
        last = result["messages"][-1]
        content = last.content if hasattr(last, "content") else last["content"]
        print(f"[{label}]")
        print(f"  reply   : {content}")
        print(f"  attempts: {result['attempts']}")
        if result.get("enrichment"):
            print(f"  enrich  : {result['enrichment']}")
        if result.get("item_results"):
            print(f"  items   : {result['item_results']}")
        print()
