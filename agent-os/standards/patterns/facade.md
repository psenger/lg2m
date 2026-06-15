# Facade Pattern — Python / LangChain

> For the language-agnostic pattern description and rationale, see `global/gang-of-four.md` (Facade section). This document provides Python / LangChain-specific rules and examples.

Provide a simplified, domain-meaningful interface to a complex LangChain pipeline. The facade hides retrievers, rerankers, prompts, LLMs, and parsers behind a single method call expressed in business terms.

---

## Rules

- The facade's public interface must use domain terms, not LangChain primitives (`answer(query)`, not `invoke_chain_with_retriever(query, retriever, llm, parser)`).
- Inject all LangChain components as constructor arguments — do not create LLMs or retrievers inside the facade.
- The facade is the composition root for a pipeline workflow; it does not contain prompt logic or domain decisions.
- Test the facade by replacing injected components with fakes — do not make real LLM calls in unit tests.
- Keep the facade's interface stable even as the internal pipeline changes.

---

## Example — RAG Pipeline Facade

```python
# app/facades/rag_pipeline_facade.py
from dataclasses import dataclass
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from app.ports.retrieval_strategy import RetrievalStrategy
from app.ports.reranking_strategy import RerankingStrategy

@dataclass(frozen=True)
class RAGRequest:
    question: str
    top_k: int = 4

@dataclass(frozen=True)
class RAGResponse:
    answer: str
    source_documents: list[str]


RAG_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant. Answer the question using only the context provided below. "
        "If the answer is not in the context, say you do not know.\n\nContext:\n{context}",
    ),
    ("human", "{question}"),
])


class RAGPipelineFacade:
    """
    Hides the retriever, reranker, prompt, LLM, and parser behind a single
    domain-facing interface: ask(question) → answer.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        retrieval_strategy: RetrievalStrategy,
        reranking_strategy: RerankingStrategy,
    ) -> None:
        self._retrieval_strategy = retrieval_strategy
        self._reranking_strategy = reranking_strategy
        self._chain = RAG_PROMPT | llm | StrOutputParser()

    async def ask(self, request: RAGRequest) -> RAGResponse:
        # 1. Retrieve candidate documents
        candidates = await self._retrieval_strategy.aretrieve(request.question, k=request.top_k * 2)

        # 2. Rerank and trim
        ranked = self._reranking_strategy.rerank(request.question, candidates, top_k=request.top_k)

        # 3. Format context
        context = "\n\n".join(doc.page_content for doc in ranked)
        sources = [doc.metadata.get("source", "unknown") for doc in ranked]

        # 4. Generate the answer
        answer = await self._chain.ainvoke({"context": context, "question": request.question})

        return RAGResponse(answer=answer, source_documents=sources)


# Usage — the caller never sees retrievers, rerankers, or prompts
async def handle_user_question(question: str) -> str:
    request = RAGRequest(question=question, top_k=4)
    response = await rag_facade.ask(request)
    return response.answer
```

---

## Example — Agent Facade

```python
# app/facades/agent_facade.py
from dataclasses import dataclass
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

@dataclass(frozen=True)
class AgentRequest:
    user_message: str
    session_id: str

@dataclass(frozen=True)
class AgentResponse:
    reply: str
    tools_used: list[str]


AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to tools. Use them when appropriate."),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


class AgentFacade:
    """
    Wraps tool loading, agent creation, and execution behind a simple interface.
    Callers invoke process(request) and receive a plain AgentResponse.
    """

    def __init__(self, llm: BaseChatModel, tools: list[BaseTool]) -> None:
        agent = create_tool_calling_agent(llm, tools, AGENT_PROMPT)
        self._executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            return_intermediate_steps=True,
            max_iterations=10,
        )

    async def process(self, request: AgentRequest) -> AgentResponse:
        result = await self._executor.ainvoke({
            "input": request.user_message,
        })

        tools_used = [
            step[0].tool
            for step in result.get("intermediate_steps", [])
        ]

        return AgentResponse(
            reply=result["output"],
            tools_used=tools_used,
        )


# Wired in the app factory
def create_agent_facade(llm: BaseChatModel) -> AgentFacade:
    from app.tools.search_tool import search_knowledge_base
    from app.tools.crm_tool import update_customer
    from app.tools.report_tool import generate_report_tool

    return AgentFacade(
        llm=llm,
        tools=[search_knowledge_base, update_customer, generate_report_tool],
    )
```

---

## Testing the Facade

Replace real LLM and retriever with lightweight fakes; test that the facade wires them correctly and returns the right shape of response.

```python
# tests/facades/test_rag_pipeline_facade.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document
from app.facades.rag_pipeline_facade import RAGPipelineFacade, RAGRequest

@pytest.fixture
def fake_retrieval_strategy():
    strategy = MagicMock()
    strategy.aretrieve = AsyncMock(return_value=[
        Document(page_content="The capital of France is Paris.", metadata={"source": "geo-facts.txt"}),
    ])
    return strategy

@pytest.fixture
def fake_reranking_strategy():
    strategy = MagicMock()
    strategy.rerank = MagicMock(side_effect=lambda query, docs, top_k: docs[:top_k])
    return strategy

@pytest.fixture
def fake_llm():
    llm = MagicMock()
    # Simulate the chain: prompt | llm | parser collapses to the fake output
    llm.invoke = MagicMock(return_value=MagicMock(content="Paris is the capital of France."))
    return llm

@pytest.mark.asyncio
async def test_ask_returns_answer_and_sources(fake_retrieval_strategy, fake_reranking_strategy, fake_llm):
    facade = RAGPipelineFacade(
        llm=fake_llm,
        retrieval_strategy=fake_retrieval_strategy,
        reranking_strategy=fake_reranking_strategy,
    )

    # Patch the internal chain so we don't need real LLM
    facade._chain = AsyncMock(return_value="Paris is the capital of France.")

    response = await facade.ask(RAGRequest(question="What is the capital of France?"))

    assert "Paris" in response.answer
    assert "geo-facts.txt" in response.source_documents
    fake_retrieval_strategy.aretrieve.assert_called_once()
    fake_reranking_strategy.rerank.assert_called_once()
```

---

## Facade Interface Design

The facade's interface should be expressed in terms of the business operation, not LangChain primitives.

```python
# Good — domain-facing interface
class DocumentQAFacade:
    async def answer_question(self, question: str, document_ids: list[str]) -> str: ...

class ContentModerationFacade:
    async def moderate(self, text: str) -> ModerationResult: ...

class DataExtractionFacade:
    async def extract_entities(self, document: str) -> list[Entity]: ...

# Avoid — leaking LangChain internals into the public interface
class LeakyFacade:
    async def run_chain(self, input_dict: dict, retriever: BaseRetriever) -> dict: ...
    # ^ callers now depend on LangChain types — breaks encapsulation
```
