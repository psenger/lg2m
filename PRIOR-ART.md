# Prior art and the novelty claim

> Where `lg2m` sits among LangGraph/LangChain diagramming, Mermaid tooling, and
> code <-> diagram sync, and exactly what about it is new. This is the long form
> of [`docs/design.md`](docs/design.md) Section 1.
>
> **Last reviewed: 2026-06-14.**

## The claim

No tool provides **bidirectional, drift-detecting sync** between a LangGraph or
LangChain graph's *topology* and a human-readable Mermaid `stateDiagram-v2`
*contract*, with scaffolding in either direction.

Every individual capability below exists in isolation. None combines them, and
none pairs topology sync with **drift-as-a-build-contract** while being
LangGraph-aware. The novelty is the *combination* and the drift-as-contract
semantics, not any single capability. The defensible phrasing is therefore the
narrow one above, not a blanket "no sync tool exists" (which the *Mermaid Diagram
Sync* app below would rebut).

## How this was assessed (validation caveat)

Assessed against each tool's published documentation and, where available, its
source, as of the review date above. Not every claim was reproduced by running
the tool. The enabling-tech layer (Section C) moves quickly (`mermaid-parser-py`
first shipped in late 2025), so the parser-availability premise in particular is
time-sensitive; re-check it before relying on it. Where a fact is volatile (a
version or an adoption number) it is marked "at review."

## The landscape

### A. One-way: code -> diagram

The largest category. These render or regenerate a diagram from code; none reads
an edited diagram back, and none treats disagreement as a failure.

- **LangGraph `draw_mermaid()`** (`compiled.get_graph().draw_mermaid()`): the
  platform's own renderer. Emits a Mermaid **flowchart only** (the generator
  hard-codes a `graph TD;` header in `graph_mermaid.py`); there is no parser to
  read a diagram back. Closest to "official," but render-only and flowchart-only.
- **LangGraph Studio**: visual viewer and debugger. Renders the compiled graph
  (code -> diagram); no code generation, no edit-back-to-code, no drift contract.
- **`python-statemachine` / `transitions`**: state-machine libraries that can
  **export** a Mermaid diagram from a machine definition. Their docs state the
  export is one-way (no import). Different domain (FSMs, not LangGraph) and
  one-directional.
- **`pyreverse`** (pylint) and the **smazee** VS Code extension: general code
  visualizers. `pyreverse` emits UML from Python source; smazee draws graphs in
  the editor with Cytoscape, not Mermaid. Viewers, not sync tools, not
  stateDiagram-v2.
- **Mermaid Diagram Sync** (GitHub marketplace app): the **strongest
  counterexample**. On a pull request it locates connected Mermaid diagrams,
  regenerates them from the changed code, and commits the result back. It
  occupies the "keep the diagram synced with the code" sentence almost verbatim.
  But it is still one-way (code -> diagram regeneration), general-purpose (not
  LangGraph-aware), has **no diagram -> code** path, and has **no fail-the-build
  drift contract**: it silently fixes the diagram rather than failing when code
  and diagram disagree.

### B. Builders: diagram / GUI -> code

- **LangGraph-GUI**: a SvelteFlow visual builder. You draw a graph and it
  produces a runnable LangGraph; build-then-run. There is no introspection
  round-trip: it does not take an *existing* compiled graph and reconcile it
  against a diagram, and it does not detect drift.

### C. Enabling tech: Python `stateDiagram-v2` parsers

This matters because `lg2m` must parse a hand-edited `stateDiagram-v2` back into
an IR. If a robust parser existed, part of `lg2m` would be off-the-shelf.

- **pyStateGram**: parses Mermaid `stateDiagram-v2`, but is parse-only (no
  emit), incomplete (no composite states, no `<<fork>>` / `<<join>>`), and low
  adoption (~2 GitHub stars at review).
- **mermaid-parser-py**: wraps Mermaid's own parser but **requires Node.js** at
  runtime and is pre-1.0 (0.0.x at review, first shipped late 2025).

No pure-Python, complete, emit-capable `stateDiagram-v2` parser exists, so
`lg2m` must build and maintain its own, covering `[else]`, `<<fork>>` /
`<<join>>`, and composite states. That is both a real cost (a substantial,
bug-prone component, `parsing/mermaid.py`) and part of the moat (time-sensitive).

## Side-by-side

Columns: which directions it supports; whether it understands LangGraph/LangChain
graphs; whether it speaks Mermaid `stateDiagram-v2`; whether it *detects* drift;
whether it can *fail a build* on drift; whether it scaffolds *both* sides.

| Tool | Direction | LG/LC-aware | stateDiagram-v2 | Drift detect | Fail-the-build | Both-way scaffold |
| --- | --- | --- | --- | --- | --- | --- |
| LangGraph `draw_mermaid()` | code -> diagram | yes | no (flowchart) | no | no | no |
| LangGraph Studio | code -> diagram (view) | yes | no (own render) | no | no | no |
| `python-statemachine` / `transitions` | code -> diagram | no | yes (export) | no | no | no |
| Mermaid Diagram Sync | code -> diagram (regen) | no | yes (any Mermaid) | regen, not a contract | no | no |
| LangGraph-GUI | diagram -> code (build) | yes | no (SvelteFlow) | no | no | no |
| pyStateGram | diagram -> IR (parse) | no | parse-only | no | no | no |
| mermaid-parser-py | diagram -> AST (parse) | no | parse (needs Node.js) | no | no | no |
| **`lg2m`** | **code <-> diagram** | **yes** (LG full, LC slice) | **yes** | **yes** | **yes** | **yes** |

## The gap `lg2m` fills

`lg2m` is the only tool that, for LangGraph/LangChain specifically, combines:

1. **bidirectional** scaffolding: code -> diagram *and* diagram -> code;
2. **topology truth by introspection** (`get_graph()`), not by redrawing;
3. **drift as a build contract**: `check` exits non-zero when code, annotations,
   and the diagram disagree;
4. a human-readable **Mermaid `stateDiagram-v2` contract** with structured
   metadata for what the diagram cannot draw;
5. **routing that cannot drift**: a generated router that owns its `path_map`, so
   labels, runtime selector, and diagram are one source.

Each of these exists somewhere in the landscape. The combination, and the
drift-as-contract framing, do not.

**Scope honesty (carried from `docs/design.md`):** full bidirectional fidelity for
LangGraph; the LCEL-expressible slice (linear chains + `RunnableBranch`) for
LangChain. The routing model is portable to both; the wider graph (parallel
fan-out with reducers, `Send`, `Command`, subgraphs) is LangGraph-only.

## What would falsify the claim

- A **LangGraph-aware** tool that both renders *and* re-ingests a Mermaid diagram
  with drift detection would compete directly. None found at review.
- If **Mermaid Diagram Sync** (or a similar app) added a diagram -> code path, a
  fail-the-build mode, and LangGraph awareness, it would close most of the gap.
  Track it; it is the nearest neighbor.
- If a **complete, pure-Python `stateDiagram-v2` parser/emitter** ships, the
  enabling-tech moat (Section C) erodes, though the LangGraph-aware
  reconciliation and contract layer would remain `lg2m`'s.
