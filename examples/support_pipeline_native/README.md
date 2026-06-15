# Example: support_pipeline_native

One comprehensive support-pipeline graph, rendered natively in two frameworks
side by side: LangGraph and LangChain (LCEL). There is no lg2m
(langgraph_to_from_mermaid) here at all, so this is the "before lg2m" picture for
the FULL surface the lg2m design targets. The LangGraph file is the complete
graph and exercises every boundary the design names; the LangChain file renders
only the slice LCEL can express, and the gap between the two is the point. The
companion directory `examples/support_pipeline/` is the same graph with lg2m
applied.

## Boundary -> construct

Each row is one boundary the canonical graph crosses. The LangGraph column is the
native construct in `langgraph_app.py`; the LangChain column is the LCEL construct
in `langchain_app.py`, or "cannot express" when there is no faithful equivalent.

| boundary | LangGraph construct | LangChain construct |
| --- | --- | --- |
| chain | `add_edge` between nodes | `\|` pipe / `RunnableSequence` |
| parallel fork / fan-in | one source with multiple out-edges, join on a shared target | `RunnableParallel`, then a manual fan-in step |
| reducer-governed merge | concurrent channel writes merged by a channel reducer | cannot express: merge is hand-written in a `RunnableLambda` |
| conditional routing + [else] | `add_conditional_edges` with a router mapping | `RunnableBranch((pred, arm), ..., default)` |
| subgraph | a compiled sub-`StateGraph` added as a node | nested `RunnableSequence` (different construct, not a sub-state) |
| Send map-reduce | `Send(...)` dynamic-width fan-out, custom reducer joins | cannot express: a plain Python loop approximates it |
| `Command(goto)` | node returns `Command(goto=...)`, routes from inside the body | cannot express: escalation is just another branch arm |
| add_messages reducer | `Annotated[list, add_messages]` channel | cannot express: list concatenation by hand |
| operator.add reducer | `Annotated[int, operator.add]` / `Annotated[list, operator.add]` | cannot express: numeric add / list append by hand |
| custom reducer | `Annotated[list, extend_unique]` channel | cannot express: dedupe loop by hand |

## What LangChain cannot express

LangChain Expression Language is a pipeline algebra, not a state machine. The
following LangGraph constructs have no faithful LCEL equivalent, so
`langchain_app.py` does not fake them; it does the work by hand and says so in
comments:

- typed state channels with reducers (`add_messages`, `operator.add`, the custom
  `extend_unique`): the LCEL "state" is a plain dict and every merge is manual.
- LangGraph `Send` dynamic map-reduce: there is no superstep barrier and no
  channel reducer, so the item loop is an approximation, not a fan-out node.
- `Command(goto=...)` routing from inside a node: LCEL has no goto, so escalation
  is simply another `RunnableBranch` arm.
- subgraphs as composite states with their own state schema: a nested chain is
  not a sub-`StateGraph`.
- `START` / `END` pseudostates and persistent channel semantics.

This asymmetry is why the lg2m design treats LangGraph as the full surface and
LangChain as the subset its Model-A routing still compiles to: the
`RunnableBranch` in `langchain_app.py` is exactly the construct Model A emits, and
everything above it on the list is LangGraph-only.

## Files

- `langgraph_app.py` (full surface, runs): the complete native graph. Exercises
  every boundary in the table, including the LangGraph-only ones.
- `langchain_app.py` (expressible slice, runs): the same pipeline for the same
  three tickets, in LCEL. Faithful where LCEL can be, manual where it cannot.
- `introspect.py` (topology dump): prints the nodes, edges, and state schema that
  lg2m would read via `compiled.get_graph(xray=True)`. Do not edit; it imports
  from `langgraph_app.py`.

## Setup and run (virtual environment)

These steps create an isolated virtual environment, install the dependencies
from `requirements.txt`, and run all three scripts. Written for macOS / zsh.

```bash
# 1. Move into this example directory
cd examples/support_pipeline_native

# 2. Create a virtual environment in a local .venv folder
python3 -m venv .venv

# 3. Activate it (zsh or bash); your prompt then shows (.venv)
source .venv/bin/activate

# 4. Install the dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 5. Run the full LangGraph graph
python langgraph_app.py

# 6. Run the LangChain (LCEL) slice
python langchain_app.py

# 7. Dump the topology lg2m would read
python introspect.py

# 8. Leave the environment when you are finished
deactivate
```

The node bodies are deterministic stand-ins (no real LLM calls and no API keys),
so the runs are reproducible.

### Expected output: `python langgraph_app.py`

```
[escalate (Command path)]
  reply   : Re: Cannot log in -- escalated: handed off to human agent queue
  attempts: 2
  enrich  : ['history: 2 prior tickets for Cannot log in', 'account: tier=enterprise']

[auto_resolve path]
  reply   : Re: How do I export? -- canned: applied known answer for already-resolved ticket
  attempts: 2
  enrich  : ['history: 2 prior tickets for How do I export?', 'account: tier=free']

[investigate (subgraph + Send) path]
  reply   : Re: Intermittent errors -- investigated: analyzed:billing, analyzed:crash, analyzed:login
  attempts: 2
  enrich  : ['history: 2 prior tickets for Intermittent errors', 'account: tier=pro']
  items   : ['analyzed:login', 'analyzed:billing', 'analyzed:crash']
```

### Expected output: `python langchain_app.py`

The replies, attempts, enrichment, and item lists match the LangGraph run; only
the branch labels differ, since the LCEL path names its arms after `RunnableBranch`
rather than the Command / subgraph / Send constructs it cannot use.

```
[escalate (branch arm 1)]
  reply   : Re: Cannot log in -- escalated: handed off to human agent queue
  attempts: 2
  enrich  : ['history: 2 prior tickets for Cannot log in', 'account: tier=enterprise']

[auto_resolve path]
  reply   : Re: How do I export? -- canned: applied known answer for already-resolved ticket
  attempts: 2
  enrich  : ['history: 2 prior tickets for How do I export?', 'account: tier=free']

[investigate (nested chain + manual map) path]
  reply   : Re: Intermittent errors -- investigated: analyzed:billing, analyzed:crash, analyzed:login
  attempts: 2
  enrich  : ['history: 2 prior tickets for Intermittent errors', 'account: tier=pro']
  items   : ['analyzed:login', 'analyzed:billing', 'analyzed:crash']
```

### Expected output: `python introspect.py`

```
=== NODES (xray=True flattens the investigate subgraph) ===
  __start__
  ingest_ticket
  fetch_history
  lookup_account
  classify_intent
  auto_resolve
  escalate_to_human
  map_items
  process_item
  reduce_items
  compose_reply
  __end__
  investigate:gather_logs
  investigate:analyze

=== EDGES (conditional flag from get_graph) ===
               __start__ -> ingest_ticket          (unconditional)
            auto_resolve -> compose_reply          (unconditional)
         classify_intent -> auto_resolve           (conditional)
         classify_intent -> escalate_to_human      (conditional)
         classify_intent -> investigate:gather_logs (conditional)
       escalate_to_human -> compose_reply          (conditional)
           fetch_history -> classify_intent        (unconditional)
           ingest_ticket -> fetch_history          (unconditional)
           ingest_ticket -> lookup_account         (unconditional)
     investigate:analyze -> map_items              (unconditional)
          lookup_account -> classify_intent        (unconditional)
               map_items -> process_item           (conditional)
            process_item -> reduce_items           (unconditional)
            reduce_items -> compose_reply          (unconditional)
           compose_reply -> __end__                (unconditional)
  investigate:gather_logs -> investigate:analyze    (unconditional)

=== STATE SCHEMA + REDUCERS ===
  ticket         Ticket     reducer=-
  messages       list       reducer=add_messages
  attempts       int        reducer=operator.add
  enrichment     list       reducer=operator.add
  flags          dict       reducer=-
  items          list       reducer=-
  item_results   list       reducer=extend_unique (custom)
  resolution     str        reducer=-
```

To start over, remove the environment with `rm -rf .venv` and repeat from step 2.
