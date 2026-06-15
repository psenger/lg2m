# Object Pool Pattern — Python / LangChain

An object pool manages a collection of reusable objects whose creation is expensive. In LangChain applications, the most relevant pool concerns are: LLM client HTTP connection pools, vector store connection pools, and concurrency limiting for LLM calls.

---

## Rules

- **Use a pool when object creation is expensive and objects can be reused.** LLM client HTTP connections, database connections (pgvector via SQLAlchemy), and Redis connections are the canonical cases.
- **LLM client HTTP pooling is handled internally by the SDK.** Most LLM provider SDKs (OpenAI, Anthropic) use `httpx` under the hood, which manages a connection pool automatically. Configure it via the client constructor rather than building a pool manually.
- **Treat shared LLM and embedding model instances as a pool of one.** The LLM client holds a connection pool and is expensive to initialise. Create it once and share it across all chains. See `lazy-loading.md` for the initialisation pattern.
- **Use `asyncio.Semaphore` as a simple concurrency pool to limit parallel LLM calls.** Rate limits on LLM APIs are enforced per minute or per second. Without concurrency limiting, a batch job can exhaust the rate limit in seconds. A semaphore caps the number of concurrent in-flight calls.
- **Always return connections to the pool.** For SQLAlchemy-backed vector stores, use the session as a context manager. For custom pools, use `try/finally`.

---

## Example 1 — LLM client HTTP connection pool configuration

The OpenAI and Anthropic SDKs accept an `http_client` parameter for configuring the underlying `httpx` connection pool. Configure this when your application makes many concurrent LLM calls.

```python
from __future__ import annotations

import httpx
import functools
from langchain_core.language_models import BaseChatModel


@functools.lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Return the shared LLM client with a configured HTTP connection pool.
    lru_cache(maxsize=1) means this is constructed exactly once.
    """
    from langchain_openai import ChatOpenAI

    # Configure the underlying httpx connection pool
    http_client = httpx.Client(
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,
            keepalive_expiry=30,
        ),
        timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
    )

    return ChatOpenAI(
        model='gpt-4o-mini',
        temperature=0,
        http_client=http_client,
        max_retries=3,
    )


@functools.lru_cache(maxsize=1)
def get_async_llm() -> BaseChatModel:
    """Async variant using httpx.AsyncClient for async chains."""
    from langchain_openai import ChatOpenAI

    async_http_client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,
        ),
        timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
    )

    return ChatOpenAI(
        model='gpt-4o-mini',
        temperature=0,
        async_client=async_http_client,
        max_retries=3,
    )
```

---

## Example 2 — Vector store connection pooling via SQLAlchemy

When using a Postgres-backed vector store (pgvector), configure the SQLAlchemy connection pool the same way as in any Python application.

```python
from __future__ import annotations

import functools
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool


@functools.lru_cache(maxsize=1)
def get_pg_engine():
    """
    Shared SQLAlchemy engine with connection pool.
    Used by the pgvector store and any other Postgres queries.
    """
    import os
    return create_engine(
        os.environ['DATABASE_URL'],
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,   # recycle connections older than 30 minutes
        pool_pre_ping=True,  # validate connections before use
    )


@functools.lru_cache(maxsize=1)
def get_vector_store():
    """
    Shared vector store backed by the shared connection pool.
    Constructed once; used by all retrieval chains.
    """
    from langchain_postgres.vectorstores import PGVector
    from langchain_openai import OpenAIEmbeddings

    return PGVector(
        embeddings=get_embeddings(),
        collection_name='documents',
        connection=get_pg_engine(),
    )
```

---

## Example 3 — `asyncio.Semaphore` as a concurrency pool

A semaphore is the simplest concurrency pool: it allows at most N operations to run concurrently. Use it to cap the number of simultaneous LLM calls in batch processing jobs.

```python
from __future__ import annotations

import asyncio
from typing import Any
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable


async def run_with_semaphore(
    chain: Runnable,
    inputs: list[dict],
    max_concurrency: int = 10,
) -> list[Any]:
    """
    Invoke a chain over a list of inputs, limiting concurrent calls to max_concurrency.
    Prevents rate limit exhaustion when processing large batches.
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def invoke_one(input_data: dict) -> Any:
        async with semaphore:
            return await chain.ainvoke(input_data)

    return await asyncio.gather(*[invoke_one(inp) for inp in inputs])


# Usage — process 1,000 documents with at most 10 concurrent LLM calls
async def summarise_batch(documents: list[str]) -> list[str]:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        ('system', 'Summarise the following text in one sentence.'),
        ('human', '{text}'),
    ])
    chain = prompt | get_async_llm() | StrOutputParser()

    inputs = [{'text': doc} for doc in documents]
    return await run_with_semaphore(chain, inputs, max_concurrency=10)
```

---

## Example 4 — Shared Pinecone client (pool of one)

The Pinecone client initialises a gRPC or HTTP connection. Treat it as a pool of one: create it once, share it everywhere.

```python
from __future__ import annotations

import functools
import os


@functools.lru_cache(maxsize=1)
def get_pinecone_index():
    """
    Shared Pinecone index client.
    Constructed once; the underlying gRPC channel is reused for all calls.
    """
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
    return pc.Index(os.environ['PINECONE_INDEX_NAME'])


@functools.lru_cache(maxsize=1)
def get_pinecone_vector_store():
    """Vector store wrapping the shared Pinecone index."""
    from langchain_pinecone import PineconeVectorStore
    return PineconeVectorStore(
        index=get_pinecone_index(),
        embedding=get_embeddings(),
    )
```

---

## Anti-Patterns

| Anti-pattern | Consequence |
|-------------|-------------|
| Constructing a new `ChatOpenAI()` inside a chain invocation function | A new HTTP connection pool is built for every invocation; connections are never reused |
| No concurrency limiting on batch LLM calls | Rate limit errors (`429`) flood in; the job fails or stalls |
| Constructing a new SQLAlchemy engine per request | Connection limit on the database server is exhausted quickly |
| Using `asyncio.gather` without a semaphore on large batches | Hundreds of concurrent LLM calls; immediate rate limiting |

---

## Related Documents

- `global/gang-of-four.md` — Flyweight: shares immutable state across many instances; Object Pool manages stateful, exclusively-held reusable instances — they are complementary, not interchangeable
