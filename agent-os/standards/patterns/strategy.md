# Strategy Pattern — Python / LangChain

> For the language-agnostic pattern description and rationale, see `global/gang-of-four.md` (Strategy section). This document provides Python / LangChain-specific rules and examples.

Define interchangeable LangChain components — retrievers, parsers, rerankers, and LLMs — behind a common Protocol so that the pipeline consumer is decoupled from any specific implementation.

---

## Rules

- Define retrieval, parsing, and reranking strategies as `typing.Protocol` interfaces.
- Inject the strategy into the chain factory; do not select it inside the chain.
- Each strategy must be independently testable without running the full pipeline.
- Name strategies after the business or retrieval concept, not the library class (e.g., `HybridRetrievalStrategy`, not `EnsembleRetrieverWrapper`).
- `BaseChatModel` itself is the Strategy interface for language models — swapping `ChatOpenAI` for `ChatAnthropic` is the Strategy pattern in action.
- Adding a new strategy must not require changes to the pipeline that uses it.

---

## Example — Retrieval Strategies

```python
# app/ports/retrieval_strategy.py
from typing import Protocol
from langchain_core.documents import Document

class RetrievalStrategy(Protocol):
    def retrieve(self, query: str, k: int = 4) -> list[Document]: ...
    async def aretrieve(self, query: str, k: int = 4) -> list[Document]: ...
```

```python
# app/strategies/dense_retrieval_strategy.py
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

class DenseRetrievalStrategy:
    """Semantic retrieval using dense vector similarity search."""

    def __init__(self, vector_store: VectorStore) -> None:
        self._vector_store = vector_store

    def retrieve(self, query: str, k: int = 4) -> list[Document]:
        return self._vector_store.similarity_search(query, k=k)

    async def aretrieve(self, query: str, k: int = 4) -> list[Document]:
        return await self._vector_store.asimilarity_search(query, k=k)
```

```python
# app/strategies/sparse_retrieval_strategy.py
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

class SparseBM25RetrievalStrategy:
    """Keyword-based retrieval using BM25."""

    def __init__(self, documents: list[Document]) -> None:
        self._retriever = BM25Retriever.from_documents(documents)

    def retrieve(self, query: str, k: int = 4) -> list[Document]:
        self._retriever.k = k
        return self._retriever.invoke(query)

    async def aretrieve(self, query: str, k: int = 4) -> list[Document]:
        self._retriever.k = k
        return await self._retriever.ainvoke(query)
```

```python
# app/strategies/hybrid_retrieval_strategy.py
from langchain_core.documents import Document
from langchain.retrievers import EnsembleRetriever
from langchain_core.vectorstores import VectorStore
from langchain_community.retrievers import BM25Retriever

class HybridRetrievalStrategy:
    """Combines dense and sparse retrieval via reciprocal rank fusion."""

    def __init__(self, vector_store: VectorStore, documents: list[Document], weights: tuple[float, float] = (0.5, 0.5)) -> None:
        dense = vector_store.as_retriever()
        sparse = BM25Retriever.from_documents(documents)
        self._retriever = EnsembleRetriever(retrievers=[dense, sparse], weights=list(weights))

    def retrieve(self, query: str, k: int = 4) -> list[Document]:
        return self._retriever.invoke(query)[:k]

    async def aretrieve(self, query: str, k: int = 4) -> list[Document]:
        results = await self._retriever.ainvoke(query)
        return results[:k]
```

```python
# app/chains/rag_chain.py — consumer; the retrieval strategy is injected
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from app.ports.retrieval_strategy import RetrievalStrategy

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer the question using only the context below.\n\nContext:\n{context}"),
    ("human", "{question}"),
])

def create_rag_chain(llm: BaseChatModel, retrieval_strategy: RetrievalStrategy):
    def retrieve_and_format(question: str) -> str:
        docs = retrieval_strategy.retrieve(question)
        return "\n\n".join(d.page_content for d in docs)

    return (
        {"context": retrieve_and_format, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
```

---

## Example — Output Format Strategies

```python
# app/ports/output_format_strategy.py
from typing import Protocol, TypeVar, Generic

T = TypeVar("T")

class OutputFormatStrategy(Protocol[T]):
    def parse(self, text: str) -> T: ...
    def get_format_instructions(self) -> str: ...
```

```python
# app/strategies/output_format_strategies.py
import json
from pydantic import BaseModel
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.output_parsers import PydanticOutputParser

class MarkdownOutputStrategy:
    """Returns the LLM output as a plain markdown string."""

    def parse(self, text: str) -> str:
        return text.strip()

    def get_format_instructions(self) -> str:
        return "Respond in well-structured markdown."


class JsonDictOutputStrategy:
    """Parses LLM output as a JSON dictionary."""

    def parse(self, text: str) -> dict:
        # Strip markdown code fences if present
        clean = text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean)

    def get_format_instructions(self) -> str:
        return "Respond with valid JSON only, no markdown fences."


class PydanticOutputStrategy[T: BaseModel]:
    """Parses LLM output into a typed Pydantic model."""

    def __init__(self, model_class: type[T]) -> None:
        self._parser = PydanticOutputParser(pydantic_object=model_class)

    def parse(self, text: str) -> T:
        return self._parser.parse(text)

    def get_format_instructions(self) -> str:
        return self._parser.get_format_instructions()
```

---

## Example — Reranking Strategies

```python
# app/ports/reranking_strategy.py
from typing import Protocol
from langchain_core.documents import Document

class RerankingStrategy(Protocol):
    def rerank(self, query: str, documents: list[Document], top_k: int = 4) -> list[Document]: ...
```

```python
# app/strategies/reranking_strategies.py
from langchain_core.documents import Document

class ScoreThresholdRerankingStrategy:
    """Filters documents below a relevance score threshold."""

    def __init__(self, threshold: float = 0.5) -> None:
        self._threshold = threshold

    def rerank(self, query: str, documents: list[Document], top_k: int = 4) -> list[Document]:
        scored = [d for d in documents if d.metadata.get("score", 1.0) >= self._threshold]
        return scored[:top_k]


class MMRRerankingStrategy:
    """Maximal Marginal Relevance — balances relevance and diversity."""

    def __init__(self, vector_store, lambda_mult: float = 0.5) -> None:
        self._vector_store = vector_store
        self._lambda_mult = lambda_mult

    def rerank(self, query: str, documents: list[Document], top_k: int = 4) -> list[Document]:
        return self._vector_store.max_marginal_relevance_search(
            query, k=top_k, lambda_mult=self._lambda_mult
        )


class CrossEncoderRerankingStrategy:
    """Uses a cross-encoder model to score query-document pairs."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list[Document], top_k: int = 4) -> list[Document]:
        pairs = [(query, doc.page_content) for doc in documents]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in ranked[:top_k]]
```

---

## The LLM as a Strategy

`BaseChatModel` is LangChain's built-in Strategy interface for language models. Any chain that accepts a `BaseChatModel` already uses the Strategy pattern — swapping the model requires no changes to the chain.

```python
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

def create_summarisation_chain(llm: BaseChatModel):
    """The chain is unaware of which model backs the strategy."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarise the following text in three bullet points."),
        ("human", "{text}"),
    ])
    return prompt | llm | StrOutputParser()


# Any of these works — the chain code never changes
chain_openai = create_summarisation_chain(ChatOpenAI(model="gpt-4o"))
chain_anthropic = create_summarisation_chain(ChatAnthropic(model="claude-3-5-sonnet-20241022"))
chain_gemini = create_summarisation_chain(ChatGoogleGenerativeAI(model="gemini-2.0-flash"))
```
