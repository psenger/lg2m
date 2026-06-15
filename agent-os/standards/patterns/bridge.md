# Bridge Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and the distinction from Adapter, see `global/gang-of-four.md` (Bridge section). This document provides Python / LangChain-specific rules and examples.

Separate an abstraction (what a thing does) from its implementation (how it is delivered) so that both can evolve independently without changes to each other.

---

## LangChain Is Designed Around Bridge

LangChain's core architecture is an intentional application of the Bridge pattern. The abstraction layer defines what a component does (a chain, a retriever, an embedding pipeline); the implementation layer defines how it is executed (which LLM, which vector store, which embedding model).

`BaseChatModel` is the implementation interface for the LLM component. Any class that inherits from `BaseChatModel` — `ChatOpenAI`, `ChatAnthropic`, `ChatBedrock`, `FakeChatModel` — can be swapped into any chain that depends on `BaseChatModel` without changing the chain logic. This is Bridge.

---

## Rules

- Depend on LangChain's base classes and interfaces (`BaseChatModel`, `BaseRetriever`, `VectorStore`, `Embeddings`) rather than concrete implementations. These are the implementation interfaces of the Bridge.
- Construct your chain abstractions to receive the implementation via dependency injection. Never hard-code a specific LLM or vector store inside a chain class.
- Both hierarchies (chain types and LLM/store implementations) extend independently. Adding a new chain type does not require changing any LLM implementation; adding a new vector store does not require changing any chain.
- In tests, swap the implementation for a test double (`FakeChatModel`, `InMemoryVectorStore`) without changing the chain under test.
- Keep chain logic free of provider-specific knowledge. If a chain contains code that only works with OpenAI or only works with Pinecone, the Bridge boundary has been crossed incorrectly.

---

## Example — DocumentProcessor abstraction × VectorStore implementations

The abstraction hierarchy is document processing logic (how documents are chunked, embedded, and stored). The implementation hierarchy is the vector store (where and how vectors are persisted). Either side can grow independently.

```python
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter


# --- Implementation interface ---
# VectorStore from langchain_core is the implementation interface.
# FAISS, Pinecone, Chroma, and InMemoryVectorStore all implement it.


# --- Abstraction ---
class DocumentProcessor:
    """
    Abstraction: knows how to process documents.
    Implementation (VectorStore) is injected — does not know which store is used.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: Embeddings,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._store     = vector_store
        self._embeddings = embeddings
        self._splitter  = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def ingest(self, documents: list[Document]) -> None:
        """Chunk, embed, and store documents."""
        chunks = self._splitter.split_documents(documents)
        self._store.add_documents(chunks)

    def search(self, query: str, k: int = 5) -> list[Document]:
        """Retrieve the most relevant chunks for a query."""
        return self._store.similarity_search(query, k=k)


# --- Concrete abstraction subclass: a processor that filters by metadata ---
class FilteredDocumentProcessor(DocumentProcessor):
    """Extends the abstraction — still works with any VectorStore."""

    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: Embeddings,
        source_filter: str,
    ) -> None:
        super().__init__(vector_store, embeddings)
        self._source_filter = source_filter

    def ingest(self, documents: list[Document]) -> None:
        filtered = [d for d in documents if d.metadata.get('source') == self._source_filter]
        super().ingest(filtered)


# --- Composition root: wire any combination ---
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

processor_faiss = DocumentProcessor(
    vector_store=FAISS.from_documents([], OpenAIEmbeddings()),
    embeddings=OpenAIEmbeddings(),
)

from langchain_chroma import Chroma
from langchain_anthropic import AnthropicEmbeddings  # hypothetical

processor_chroma = DocumentProcessor(
    vector_store=Chroma(collection_name='docs'),
    embeddings=AnthropicEmbeddings(),
)

# Both processors have the same interface. The chain that uses them
# depends only on DocumentProcessor, not on FAISS or Chroma.
```

```python
# --- In tests: swap the implementation ---
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.embeddings.fake import FakeEmbeddings

def test_document_processor_indexes_and_retrieves():
    embeddings  = FakeEmbeddings(size=128)
    store       = InMemoryVectorStore(embeddings)
    processor   = DocumentProcessor(vector_store=store, embeddings=embeddings)

    docs = [Document(page_content='LangChain uses the Bridge pattern.')]
    processor.ingest(docs)

    results = processor.search('Bridge pattern')
    assert len(results) > 0
    assert 'Bridge' in results[0].page_content
```

---

## Example — Chain abstraction × LLM implementation

```python
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


# BaseChatModel is the implementation interface.
# ChatOpenAI, ChatAnthropic, ChatBedrock, FakeChatModel all implement it.

class SummarisationChain:
    """
    Abstraction: knows how to summarise text.
    LLM implementation is injected.
    """

    _PROMPT = ChatPromptTemplate.from_messages([
        ('system', 'Summarise the following text in {max_sentences} sentences.'),
        ('human', '{text}'),
    ])

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm | StrOutputParser()

    def summarise(self, text: str, max_sentences: int = 3) -> str:
        return self._chain.invoke({'text': text, 'max_sentences': max_sentences})


class BulletPointChain:
    """Different abstraction — same implementation interface."""

    _PROMPT = ChatPromptTemplate.from_messages([
        ('system', 'Convert the following text into {num_bullets} bullet points.'),
        ('human', '{text}'),
    ])

    def __init__(self, llm: BaseChatModel) -> None:
        self._chain = self._PROMPT | llm | StrOutputParser()

    def convert(self, text: str, num_bullets: int = 5) -> str:
        return self._chain.invoke({'text': text, 'num_bullets': num_bullets})
```

```python
# --- In tests: FakeChatModel is the test implementation ---
from langchain_core.messages import AIMessage

def fake_llm_with_response(response: str) -> BaseChatModel:
    from langchain_core.language_models.fake_chat_models import FakeChatModel
    return FakeChatModel(responses=[AIMessage(content=response)])


def test_summarisation_chain():
    llm   = fake_llm_with_response('This is a summary.')
    chain = SummarisationChain(llm=llm)
    result = chain.summarise('A long document about something...')
    assert result == 'This is a summary.'
```

---

## Related Documents

- `global/gang-of-four.md` — Bridge section for the language-agnostic pattern and distinction from Adapter
- `global/hexagonal-architecture.md` — the LLM and vector store interfaces are driven ports; concrete LangChain implementations are adapters
- `global/solid.md` — the Open/Closed Principle (OCP): new chain types or new LLM providers can be added without modifying existing code
