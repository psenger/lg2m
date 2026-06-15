# Repository Pattern — Python / LangChain

> For the language-agnostic pattern rationale, see `global/hexagonal-architecture.md` and `global/gang-of-four.md`. In LangChain applications the Repository pattern applies to both traditional data persistence and vector store operations. This document provides Python / LangChain-specific rules and examples.

The Repository pattern provides a collection-like interface for accessing domain objects, hiding all persistence details behind a typed Protocol. In LangChain applications this extends naturally to vector stores, document stores, and conversation history backends.

---

## Rules

- Define a Repository Protocol in terms of your domain model, not the persistence technology.
- Chain factories must not import SQLAlchemy, Chroma, Pinecone, or any other storage library directly — accept repository Protocols instead.
- One Repository Protocol per aggregate root or primary domain concept (users, documents, conversations).
- Repositories return domain objects or LangChain `Document` instances — never raw ORM models or library-specific objects that leak into the chain.
- Filter and query methods should be named in domain language.
- Tests use an in-memory fake repository implementing the same Protocol — never mock the repository method-by-method.
- Vector repository operations (`similarity_search`) belong behind a Protocol just as SQL operations do — the chain must not know whether the backend is Chroma, Pinecone, or pgvector.

---

## Example — Document Repository

```python
# app/ports/document_repository.py
from typing import Protocol
from langchain_core.documents import Document


class DocumentRepository(Protocol):
    def add_documents(self, documents: list[Document]) -> list[str]: ...
    def get_by_id(self, doc_id: str) -> Document | None: ...
    def delete(self, doc_id: str) -> None: ...
```

---

## Example — Vector Repository

```python
# app/ports/vector_repository.py
from typing import Protocol
from langchain_core.documents import Document


class VectorRepository(Protocol):
    def add_documents(self, documents: list[Document]) -> list[str]: ...
    def similarity_search(self, query: str, k: int = 4) -> list[Document]: ...
    def delete(self, doc_ids: list[str]) -> None: ...
```

```python
# app/adapters/chroma_vector_repository.py
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class ChromaVectorRepository:
    """Implements VectorRepository using Chroma."""

    def __init__(self, collection_name: str, embeddings: Embeddings) -> None:
        self._store = Chroma(collection_name=collection_name, embedding_function=embeddings)

    def add_documents(self, documents: list[Document]) -> list[str]:
        return self._store.add_documents(documents)

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        return self._store.similarity_search(query, k=k)

    def delete(self, doc_ids: list[str]) -> None:
        self._store.delete(ids=doc_ids)
```

```python
# app/adapters/in_memory_vector_repository.py — for tests
from langchain_core.documents import Document


class InMemoryVectorRepository:
    """In-memory VectorRepository for use in tests. Returns documents by simple string matching."""

    def __init__(self) -> None:
        self._documents: list[Document] = []

    def add_documents(self, documents: list[Document]) -> list[str]:
        self._documents.extend(documents)
        return [str(i) for i in range(len(self._documents) - len(documents), len(self._documents))]

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        # Naive keyword match sufficient for unit tests
        matched = [d for d in self._documents if query.lower() in d.page_content.lower()]
        return matched[:k] if matched else self._documents[:k]

    def delete(self, doc_ids: list[str]) -> None:
        pass  # Not required for test scenarios
```

---

## Example — Conversation Repository

```python
# app/ports/conversation_repository.py
from typing import Protocol
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ConversationMessage:
    role: str  # 'human' | 'ai' | 'system'
    content: str
    created_at: datetime


class ConversationRepository(Protocol):
    def get_history(self, session_id: str) -> list[ConversationMessage]: ...
    def append_message(self, session_id: str, message: ConversationMessage) -> None: ...
    def clear(self, session_id: str) -> None: ...
```

```python
# app/adapters/in_memory_conversation_repository.py — for tests
from collections import defaultdict
from app.ports.conversation_repository import ConversationMessage


class InMemoryConversationRepository:
    """In-memory ConversationRepository for use in tests."""

    def __init__(self) -> None:
        self._store: dict[str, list[ConversationMessage]] = defaultdict(list)

    def get_history(self, session_id: str) -> list[ConversationMessage]:
        return list(self._store[session_id])

    def append_message(self, session_id: str, message: ConversationMessage) -> None:
        self._store[session_id].append(message)

    def clear(self, session_id: str) -> None:
        self._store[session_id] = []
```

```python
# app/adapters/postgres_conversation_repository.py
from datetime import datetime
from sqlalchemy.orm import Session
from app.ports.conversation_repository import ConversationMessage


class PostgresConversationRepository:
    """Persists conversation history in PostgreSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_history(self, session_id: str) -> list[ConversationMessage]:
        rows = self._session.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = :sid ORDER BY created_at",
            {"sid": session_id},
        ).fetchall()
        return [ConversationMessage(role=r.role, content=r.content, created_at=r.created_at) for r in rows]

    def append_message(self, session_id: str, message: ConversationMessage) -> None:
        self._session.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (:sid, :role, :content, :ts)",
            {"sid": session_id, "role": message.role, "content": message.content, "ts": message.created_at},
        )
        self._session.commit()

    def clear(self, session_id: str) -> None:
        self._session.execute("DELETE FROM messages WHERE session_id = :sid", {"sid": session_id})
        self._session.commit()
```

```python
# app/chains/chat_chain.py — chain factory accepts repositories, imports no storage libraries
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.ports.conversation_repository import ConversationRepository, ConversationMessage
from datetime import datetime, timezone


def create_chat_chain(llm: BaseChatModel, conversation_repo: ConversationRepository, vector_repo):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Use the context provided to answer questions."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    chain = prompt | llm | StrOutputParser()

    def invoke(session_id: str, question: str) -> str:
        history = conversation_repo.get_history(session_id)
        messages = [
            HumanMessage(content=m.content) if m.role == "human" else AIMessage(content=m.content)
            for m in history
        ]
        answer = chain.invoke({"history": messages, "question": question})
        conversation_repo.append_message(session_id, ConversationMessage(
            role="human", content=question, created_at=datetime.now(timezone.utc),
        ))
        conversation_repo.append_message(session_id, ConversationMessage(
            role="ai", content=answer, created_at=datetime.now(timezone.utc),
        ))
        return answer

    return invoke
```

---

## Related Documents

- `global/hexagonal-architecture.md` — the Repository is a driven port; this document shows the LangChain implementation
- `global/gang-of-four.md` — Repository is related to the Proxy and Facade patterns
- `global/solid.md` — DIP: chain factories depend on Protocols, not concrete storage adapters
- `global/dry.md` — one authoritative mapping between storage rows and domain objects lives in the repository adapter
