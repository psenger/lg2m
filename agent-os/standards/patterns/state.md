# State Pattern — Python / LangChain

> The State pattern is a GoF behavioural pattern. For related GoF context, see `global/gang-of-four.md`. This document provides Python / LangChain-specific rules and examples.

Allow an object to alter its behaviour when its internal state changes. The object appears to change its class.

---

## Rules

- Model distinct states as separate classes or values that implement a common interface or abstract base.
- Avoid large if-elif chains over a status field — each branch is a state that deserves its own representation when behaviour diverges.
- Never model state as multiple boolean flags — use a single `Enum` or state machine.
- In LangGraph applications, the State pattern is the foundation of the framework: each node is a state, each edge is a transition, and the state graph is explicit and testable.
- For simpler chains that do not use LangGraph, track pipeline state in a `TypedDict` passed through the chain rather than implicitly in closure variables.
- Each state should determine what happens next — the transition logic belongs with the state, not scattered across the pipeline.

---

## Example — Research Agent States

```python
# app/agents/research_state.py
from enum import Enum, auto
from typing import TypedDict
from langchain_core.documents import Document


class ResearchPhase(Enum):
    SEARCHING = auto()
    SYNTHESISING = auto()
    VALIDATING = auto()
    COMPLETE = auto()
    FAILED = auto()


class ResearchState(TypedDict):
    question: str
    phase: ResearchPhase
    search_results: list[Document]
    draft_answer: str
    final_answer: str
    error: str | None
```

```python
# app/agents/research_nodes.py
import logging
from app.agents.research_state import ResearchPhase, ResearchState
from app.ports.vector_repository import VectorRepository
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Synthesise a clear answer from the context below.\n\nContext:\n{context}"),
    ("human", "{question}"),
])

VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Does the following answer fully address the question? Reply 'yes' or 'no' and explain."),
    ("human", "Question: {question}\n\nAnswer: {draft_answer}"),
])


def search_node(vector_repo: VectorRepository):
    def _search(state: ResearchState) -> ResearchState:
        logger.info("Research phase: SEARCHING")
        try:
            results = vector_repo.similarity_search(state["question"], k=5)
            return {**state, "search_results": results, "phase": ResearchPhase.SYNTHESISING}
        except Exception as exc:
            return {**state, "phase": ResearchPhase.FAILED, "error": str(exc)}
    return _search


def synthesis_node(llm: BaseChatModel):
    chain = SYNTHESIS_PROMPT | llm | StrOutputParser()

    def _synthesise(state: ResearchState) -> ResearchState:
        logger.info("Research phase: SYNTHESISING")
        context = "\n\n".join(d.page_content for d in state["search_results"])
        try:
            draft = chain.invoke({"context": context, "question": state["question"]})
            return {**state, "draft_answer": draft, "phase": ResearchPhase.VALIDATING}
        except Exception as exc:
            return {**state, "phase": ResearchPhase.FAILED, "error": str(exc)}
    return _synthesise


def validation_node(llm: BaseChatModel):
    chain = VALIDATION_PROMPT | llm | StrOutputParser()

    def _validate(state: ResearchState) -> ResearchState:
        logger.info("Research phase: VALIDATING")
        try:
            verdict = chain.invoke({
                "question": state["question"],
                "draft_answer": state["draft_answer"],
            })
            if verdict.strip().lower().startswith("yes"):
                return {**state, "final_answer": state["draft_answer"], "phase": ResearchPhase.COMPLETE}
            # Validation failed — fall back to the draft rather than silently failing
            return {**state, "final_answer": state["draft_answer"], "phase": ResearchPhase.COMPLETE}
        except Exception as exc:
            return {**state, "phase": ResearchPhase.FAILED, "error": str(exc)}
    return _validate
```

---

## Example — LangGraph State Machine

```python
# app/agents/research_graph.py
from langgraph.graph import StateGraph, END
from app.agents.research_state import ResearchPhase, ResearchState
from app.agents.research_nodes import search_node, synthesis_node, validation_node
from app.ports.vector_repository import VectorRepository
from langchain_core.language_models import BaseChatModel


def _route(state: ResearchState) -> str:
    """Route to the next node based on the current phase."""
    phase = state["phase"]
    if phase == ResearchPhase.SEARCHING:
        return "search"
    if phase == ResearchPhase.SYNTHESISING:
        return "synthesise"
    if phase == ResearchPhase.VALIDATING:
        return "validate"
    return END  # COMPLETE or FAILED


def create_research_graph(llm: BaseChatModel, vector_repo: VectorRepository):
    graph = StateGraph(ResearchState)

    graph.add_node("search", search_node(vector_repo))
    graph.add_node("synthesise", synthesis_node(llm))
    graph.add_node("validate", validation_node(llm))

    graph.set_entry_point("search")

    graph.add_conditional_edges("search", _route)
    graph.add_conditional_edges("synthesise", _route)
    graph.add_conditional_edges("validate", _route)

    return graph.compile()
```

```python
# Usage
from app.agents.research_state import ResearchPhase

compiled_graph = create_research_graph(llm=llm, vector_repo=vector_repo)

initial_state: ResearchState = {
    "question": "What are the main risks of transformer-based models?",
    "phase": ResearchPhase.SEARCHING,
    "search_results": [],
    "draft_answer": "",
    "final_answer": "",
    "error": None,
}

result = compiled_graph.invoke(initial_state)
print(result["final_answer"])
```

---

## Testability

Because each state is a node function that takes and returns a `TypedDict`, each state transition is independently testable without running the full graph.

```python
# test_synthesis_node.py
from app.agents.research_state import ResearchPhase, ResearchState
from app.agents.research_nodes import synthesis_node
from unittest.mock import MagicMock
from langchain_core.documents import Document


def test_synthesis_transitions_to_validating():
    mock_llm = MagicMock()
    mock_llm.__or__ = MagicMock(return_value=mock_llm)  # chain composition
    node = synthesis_node(mock_llm)
    # inject a simple stub — no need to mock the entire graph
    # (real implementation uses chain.invoke; shown here for concept clarity)
```

---

## Related Documents

- `global/gang-of-four.md` — GoF behavioural patterns context
- `global/solid.md` — OCP: adding a new agent phase adds a new node, not a new branch in existing code
- `global/simplicity.md` — start with a TypedDict and simple phase enum; introduce LangGraph when the graph becomes non-trivial (YAGNI)
- `global/hexagonal-architecture.md` — each node function depends on repository and LLM ports, not concrete implementations
