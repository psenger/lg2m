# Singleton Pattern — Python / LangChain

> For the language-agnostic pattern description and the reasons to avoid it in favour of dependency injection, see `global/gang-of-four.md` (Singleton section). This document provides Python / LangChain-specific guidance.

Ensure expensive resources have exactly one instance throughout the application lifecycle.

---

## Module-Level Singleton (Preferred)

### Rules

- Python modules are cached after first import — exporting an instance is the simplest singleton.
- Use for: LLM clients, embedding models, vector store connections.
- This is the idiomatic Python approach — no metaclass gymnastics.

### Example

```python
# services/llm_service.py
from langchain_openai import ChatOpenAI
from app.config.settings import get_settings

settings = get_settings()

# Module-level singleton — created once, shared everywhere
llm = ChatOpenAI(
    model=settings.llm_model,
    temperature=settings.llm_temperature,
)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
```

---

## Lazy Singleton

### Rules

- Use when the resource is expensive and may not be needed in every code path.
- Initialize on first access, cache for subsequent calls.
- Useful for vector store connections that require API calls to initialize.

### Example

```python
from functools import lru_cache
from langchain_core.language_models import BaseChatModel

@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Lazily create and cache the LLM instance."""
    settings = get_settings()
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=settings.llm_model, temperature=settings.llm_temperature)

@lru_cache(maxsize=1)
def get_vector_store():
    """Lazily create and cache the vector store connection."""
    settings = get_settings()
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=get_embeddings(),
    )
```

---

## When NOT to Use Singletons

### Rules

- Do not make chains singletons — they should be created via factories for testability.
- Do not make agents singletons — they may hold conversational state.
- Singletons are for stateless resources: LLM clients, embeddings, vector store connections.
- In tests, you need to replace singletons — use DI instead of `lru_cache` when testability matters.

```python
# GOOD — LLM is singleton (stateless client), chain is created fresh
llm = get_llm()  # singleton
chain = create_summarize_chain(llm)  # fresh instance, testable
```
