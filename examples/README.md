# lg2m examples

A worked example of the `langgraph_to_from_mermaid` (`lg2m`) design from the
repo-root `docs/design.md`. It comes as a **pair**: a native version (plain LangGraph /
LangChain, the "before lg2m" code a developer writes today) and an lg2m-applied
version (the same graph annotated, plus its Mermaid + Markdown contract). The
native version runs; the lg2m-applied version imports the `lg2m` package, which
is not built yet, so it is illustrative and its `lg2m ...` transcripts are mocks.

## The pair: `support_pipeline_native` + `support_pipeline`

One connected graph designed to cross **every boundary the plan names, once**.

| | directory | runs? | what it is |
| --- | --- | --- | --- |
| native | `support_pipeline_native/` | yes | the full graph in **both** LangGraph (`langgraph_app.py`, complete surface) and LangChain (`langchain_app.py`, the slice LCEL can express), plus `introspect.py` which dumps the topology lg2m reads via `get_graph(xray=True)` |
| applied | `support_pipeline/` | no (illustrative) | the same graph with lg2m's **Model-A** annotations (`@node`, `@predicate`, `lg2m.router` + `lg2m.ELSE`, `@state_model`, `@data_model`) and `docs/support_pipeline.md`, the topological Mermaid + Markdown-metadata contract |

The two halves share an identical topology by construction: `support_pipeline`'s
`graph.py` is `support_pipeline_native`'s `langgraph_app.py` with annotations
added and the hand-written router replaced by a generated `lg2m.router(...)`
mapping. Run `support_pipeline_native/introspect.py` to see the exact nodes,
edges, conditional flags, and reducers that the applied version's diagram and
`lg2m check` transcript are written against.

## Boundary coverage

Every boundary from the plan, the LangGraph construct that expresses it, and
whether LangChain (LCEL) has a faithful equivalent.

| boundary | LangGraph construct | expressible in LangChain? |
| --- | --- | --- |
| sequential chain | `add_edge` | yes (`\|` / `RunnableSequence`) |
| conditional routing + required `[else]` | `add_conditional_edges` + router mapping | yes (`RunnableBranch` + default) |
| parallel fork / fan-in | multiple out-edges, shared join target | partial (`RunnableParallel` + manual fan-in) |
| reducer-governed merge | concurrent channel writes + reducer | no (manual merge) |
| subgraph (composite state) | compiled sub-`StateGraph` as a node | no (nested chain only) |
| `Send` dynamic map-reduce | `Send(...)` fan-out + join | no (manual loop) |
| `Command(goto)` from inside a node | `Command(goto=, destinations=)` | no (another branch arm) |
| reducers: `add_messages`, `operator.add`, custom | `Annotated[T, reducer]` channels | no (hand-written merges) |
| three Markdown-metadata forms (table / hidden fence / note) | n/a (documentation contract) | n/a |

The boundaries that LangChain cannot express are the reason the lg2m design treats
LangGraph as the full surface and LangChain as the subset its Model-A routing
still compiles to. `support_pipeline_native/README.md` has the per-construct
breakdown and the exact places LCEL forced manual work.

## Running the native example

The native directory is self-contained with its own `requirements.txt`. From
`support_pipeline_native`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python langgraph_app.py        # the full graph
python langchain_app.py        # the LCEL slice
python introspect.py           # the topology lg2m would read
deactivate
```

Node bodies are deterministic stand-ins (no LLM calls, no API keys), so every run
is reproducible. See the directory's own `README.md` for expected output.
