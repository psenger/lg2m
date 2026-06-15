"""support_pipeline_native (LangChain): the slice the same graph can express in LCEL.

This is the LangChain half of the native pair. It renders the SAME support
pipeline as `langgraph_app.py`, for the same three demo tickets, using only
LangChain Expression Language (LCEL): the pipe operator / RunnableSequence,
RunnableParallel, RunnableBranch, and RunnableLambda. The node bodies are copied
in spirit from `langgraph_app.py` so the final replies match.

What this file mirrors faithfully:

  - chain edges ............... RunnableSequence via the `|` pipe operator
  - parallel fork ............. RunnableParallel runs fetch_history and
                               lookup_account, then a RunnableLambda merges the
                               returned dict into one enrichment list BY HAND,
                               because LangChain has no channel reducer
  - conditional routing ....... RunnableBranch over should_escalate /
                               should_auto_resolve / investigate-default; this is
                               the construct lg2m's Model A compiles a router to
  - required [else] default ... the third RunnableBranch arm (investigate)
  - investigate map-reduce .... an investigate step, then a plain Python loop over
                               items inside a RunnableLambda, then a reduce step

What this file CANNOT mirror, and does not fake (see README for the full list):

  - typed state channels with reducers (add_messages / operator.add / custom):
    the "state" here is a plain dict threaded through the chain, and every merge
    (enrichment, attempts, item_results) is written out by hand
  - LangGraph `Send` dynamic map-reduce: no superstep barrier and no channel
    reducer; the item loop below is a manual approximation, not a fan-out node
  - `Command(goto=...)` routing from inside a node: LCEL has no goto, so
    escalation is simply another RunnableBranch arm
  - subgraphs as composite states with their own schema: `investigate` here is a
    nested RunnableSequence, which is not the same construct as a sub-StateGraph
  - START / END pseudostates and persistent channel semantics

Node bodies are deterministic stand-ins (no LLM, no API keys) so the run is
reproducible. `python langchain_app.py` drives one ticket down each of the three
branches and prints the reply and attempt count of each.
"""

from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
)
from pydantic import BaseModel


# --- Data model (identical to langgraph_app.py) ------------------------------

class Ticket(BaseModel):
    subject: str
    body: str
    priority: str          # 'low' | 'normal' | 'high'
    customer_tier: str     # 'free' | 'pro' | 'enterprise'


# --- State helpers -----------------------------------------------------------
# LCEL has no typed channels and no reducers. The "state" is a plain dict; every
# step returns a NEW dict so the chain stays functional. There is no add_messages,
# no operator.add, and no custom reducer, so the merges below are all manual.

def _merge(state: dict, **updates) -> dict:
    """Shallow-copy the state dict and apply updates. Stand-in for the channel
    write that LangGraph would route through a reducer; here it is a plain merge."""
    out = dict(state)
    out.update(updates)
    return out


# --- Chain steps (node bodies mirror langgraph_app.py) -----------------------

def ingest_ticket(state: dict) -> dict:
    raw = state.get("ticket")
    ticket = raw if isinstance(raw, Ticket) else Ticket(**dict(raw or {}))
    body = ticket.body.lower()
    # Derive the work items the investigate path will map over.
    signals = [tok for tok in ("login", "billing", "timeout", "crash", "data")
               if tok in body]
    return _merge(
        state,
        ticket=ticket,
        items=signals or ["general"],
        messages=state.get("messages", []) + [
            {"role": "system", "content": f"ingested: {ticket.subject}"}],
        attempts=state.get("attempts", 0) + 1,
    )


def fetch_history(state: dict) -> dict:
    # Parallel branch A. In LangGraph this writes the shared `enrichment` channel
    # (operator.add). Here it just returns its contribution; enrich_merge below
    # does the combining by hand.
    return {"enrichment": [f"history: 2 prior tickets for {state['ticket'].subject}"]}


def lookup_account(state: dict) -> dict:
    # Parallel branch B. Also contributes to `enrichment`.
    tier = state["ticket"].customer_tier
    return {"enrichment": [f"account: tier={tier}"]}


def enrich_merge(parts: dict) -> dict:
    """Fan-in for the RunnableParallel above.

    NOTE: LangChain has no channel reducer. RunnableParallel hands back a dict
    {"state": <upstream state>, "history": {...}, "account": {...}}; we merge the
    two enrichment contributions into one list by hand, in branch order, which is
    what operator.add would have done across the two concurrent channel writes.
    """
    state = parts["state"]
    enrichment = parts["history"]["enrichment"] + parts["account"]["enrichment"]
    return _merge(state, enrichment=enrichment)


def classify_intent(state: dict) -> dict:
    # Fan-in point of the parallel enrichment, and the conditional source.
    ticket = state["ticket"]
    body = ticket.body.lower()
    flags = {
        "urgent": ticket.priority == "high" or "asap" in body,
        "vip": ticket.customer_tier == "enterprise",
        "resolved": "already solved" in body or "resolved" in body,
        "has_attachment": "attachment" in body or "see attached" in body,
    }
    return _merge(
        state,
        flags=flags,
        messages=state["messages"] + [{"role": "system", "content": "classified"}],
    )


def auto_resolve(state: dict) -> dict:
    return _merge(
        state,
        resolution="canned: applied known answer for already-resolved ticket",
        attempts=state["attempts"] + 1,
    )


def escalate_to_human(state: dict) -> dict:
    # In LangGraph this node uses Command(goto="compose_reply"). LCEL has no goto;
    # this is simply the first RunnableBranch arm and flows on to compose_reply
    # like any other step.
    return _merge(
        state,
        resolution="escalated: handed off to human agent queue",
        messages=state["messages"] + [
            {"role": "system", "content": "handoff -> human queue"}],
        attempts=state["attempts"] + 1,
    )


# --- investigate: nested chain + manual map-reduce ---------------------------
# In LangGraph `investigate` is a compiled sub-StateGraph (gather_logs -> analyze)
# and the map-reduce is a dynamic-width Send fan-out merged by a custom reducer.
# Here `investigate` is a nested RunnableSequence and the map is a plain Python
# loop. There is no superstep barrier and no channel reducer; this is an
# approximation of Send, not the same construct.

def gather_logs(state: dict) -> dict:
    return _merge(
        state,
        messages=state["messages"] + [
            {"role": "system",
             "content": f"gathered logs for {len(state['items'])} signal(s)"}],
    )


def analyze(state: dict) -> dict:
    return _merge(
        state,
        messages=state["messages"] + [{"role": "system", "content": "analyzed logs"}],
    )


def process_item(item: str) -> str:
    # One "worker" per item. In LangGraph this is a Send worker writing
    # item_results, merged by the extend_unique custom reducer.
    return f"analyzed:{item}"


def map_items(state: dict) -> dict:
    state = _merge(
        state,
        messages=state["messages"] + [
            {"role": "system", "content": f"mapping {len(state['items'])} item(s)"}],
    )
    # Manual map: a plain comprehension stands in for the Send fan-out. The
    # extend_unique reducer's dedupe is done by hand here.
    results: list = []
    for item in state["items"]:
        analyzed = process_item(item)
        if analyzed not in results:
            results.append(analyzed)
    return _merge(state, item_results=results)


def reduce_items(state: dict) -> dict:
    # Join after the manual map. Mirrors reduce_items in langgraph_app.py.
    found = ", ".join(sorted(state.get("item_results", [])))
    return _merge(state, resolution=f"investigated: {found}", attempts=state["attempts"] + 1)


# investigate as a nested RunnableSequence: gather_logs -> analyze -> map -> reduce.
investigate_chain = (
    RunnableLambda(gather_logs)
    | RunnableLambda(analyze)
    | RunnableLambda(map_items)
    | RunnableLambda(reduce_items)
)


def compose_reply(state: dict) -> dict:
    resolution = state.get("resolution", "")
    reply = f"Re: {state['ticket'].subject} -- {resolution}"
    return _merge(
        state,
        messages=state["messages"] + [{"role": "assistant", "content": reply}],
    )


# --- Conditional routing -----------------------------------------------------
# These are the leaf predicates lg2m's Model A would name with @predicate. They
# are identical to langgraph_app.py's predicates.

def should_escalate(state: dict) -> bool:
    f = state["flags"]
    return (f.get("urgent") or f.get("vip")) and not f.get("resolved")


def should_auto_resolve(state: dict) -> bool:
    f = state["flags"]
    return bool(f.get("resolved")) and not f.get("has_attachment")


# The RunnableBranch is the LCEL construct lg2m's Model A targets. First match
# wins; the final positional arm is the required [else] default (investigate).
route_branch = RunnableBranch(
    (RunnableLambda(should_escalate), RunnableLambda(escalate_to_human)),
    (RunnableLambda(should_auto_resolve), RunnableLambda(auto_resolve)),
    investigate_chain,                                      # [else] default
)


# --- Pipeline assembly -------------------------------------------------------
# START -> ingest -> (parallel enrich) -> classify -> branch -> compose -> END
# The pipe operator is the chain; RunnableParallel is the fork; enrich_merge is
# the hand-written join.

enrich_parallel = RunnableParallel(
    state=RunnableLambda(lambda s: s),       # carry the upstream state forward
    history=RunnableLambda(fetch_history),
    account=RunnableLambda(lookup_account),
)

pipeline = (
    RunnableLambda(ingest_ticket)
    | enrich_parallel
    | RunnableLambda(enrich_merge)
    | RunnableLambda(classify_intent)
    | route_branch
    | RunnableLambda(compose_reply)
)


# --- Demo (same three tickets as langgraph_app.py) ---------------------------

_TICKETS = {
    "escalate (branch arm 1)": Ticket(
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
    "investigate (nested chain + manual map) path": Ticket(
        subject="Intermittent errors",
        body="login times out and billing crash on submit",
        priority="normal",
        customer_tier="pro",
    ),
}


def _run_one(ticket: Ticket) -> dict:
    return pipeline.invoke({
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
    for label, ticket in _TICKETS.items():
        result = _run_one(ticket)
        content = result["messages"][-1]["content"]
        print(f"[{label}]")
        print(f"  reply   : {content}")
        print(f"  attempts: {result['attempts']}")
        if result.get("enrichment"):
            print(f"  enrich  : {result['enrichment']}")
        if result.get("item_results"):
            print(f"  items   : {result['item_results']}")
        print()
