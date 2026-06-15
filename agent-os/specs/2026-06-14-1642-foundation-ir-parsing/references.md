# References for the Foundation Layer

## Similar Implementations

### support_pipeline (annotated golden fixture — the oracle)

- **Location:** `examples/support_pipeline/`
- **Relevance:** This is the contract every acceptance criterion is measured
  against. It is illustrative (it imports lg2m decorators, so it cannot run until
  later layers ship), but its Markdown contract and config are exactly what the
  foundation parsers must consume.
- **Key files:**
  - `docs/support_pipeline.md` — the Markdown contract. Frontmatter
    (`lg2m_graph: support_pipeline`), `## Index`, `## Graph` (the
    `stateDiagram-v2` block), `## Data Models`, `## Predicates`, `## Nodes`,
    `## Edges`, plus the three metadata forms (visible table, hidden
    `<!-- lg2m: ... -->` fence, `> Note:`). **Read-only; do not modify** — the
    parsers conform to it, not the other way around.
  - `lg2m.toml` — `[tool.lg2m.graphs.support_pipeline]` with `graph`,
    `markdown`, `sys_path`, `xray`. Fixture for AC-01/02/03.
  - `src/support_pipeline/{state,nodes,predicates,routing,graph}.py` — the
    annotated code the markdown describes. The foundation layer does **not**
    import or introspect this; it is here only to show what the Data Models /
    Predicates / routing the markdown documents correspond to.
- **What to borrow:** the exact diagram vocabulary and metadata shapes. Every
  count in the ACs (15 states, 17 edge-table rows, 6 meta items, 8+4 model
  attributes) is read off `docs/support_pipeline.md`.

### support_pipeline_native (runnable baseline)

- **Location:** `examples/support_pipeline_native/`
- **Relevance:** The same graph as plain, runnable LangGraph and LangChain code,
  with no lg2m dependency. Not consumed by the foundation layer, but it is the
  ground truth for what the diagram *means* (fork/join, conditional routing with
  `[else]`, `Command(goto)`, `Send`, the `investigate` subgraph, three reducer
  kinds) and will be the introspection fixture in layer 3.
- **Key files:** `langgraph_app.py` (full surface), `langchain_app.py` (LCEL
  slice), `introspect.py` (a topology dump showing what `get_graph(xray=True)`
  exposes), `requirements.txt`.
- **What to borrow:** confirmation that the diagram's Send/Command edges are
  ordinary edges at the diagram level (their dynamic/inline nature is metadata),
  which is exactly AC-10.

## Design of Record

- `docs/design.md` — Section 5 (package layout), Section 6 (the IR field list and
  identity rules), Section 7 (the Markdown contract grammar and the three
  metadata mechanisms). The foundation implements these three sections.
- `PRIOR-ART.md` — why lg2m owns its own `stateDiagram-v2` parser/emitter (no
  robust Python parser exists to reuse), which is the justification for the
  hand-rolled `parsing/mermaid.py`.
