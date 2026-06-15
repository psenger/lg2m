# Lazy Loading — Python / LangChain

Lazy loading defers the initialisation of an expensive resource until the first time it is actually needed. In LangChain applications, the most important lazy loading targets are LLM clients, embedding models, vector store connections, and tool definitions — all of which are expensive to initialise and may not be needed in every code path.

---

## Rules

- **Do not instantiate LLM clients or embedding models at module load time.** Module-level construction runs at import time, which affects startup time, consumes API client resources before they are needed, and makes testing harder. Use a factory function instead.
- **Use `functools.lru_cache(maxsize=1)` as the standard lazy singleton pattern.** The factory function is called once on first invocation; subsequent calls return the cached instance. `maxsize=1` means exactly one instance is retained.
- **Lazy loading and the Flyweight pattern are complementary.** `lru_cache(maxsize=1)` is both: it defers construction (lazy loading) and shares the single instance across all callers (flyweight). They are the same mechanism applied for two different reasons.
- **Connect to vector stores lazily.** A connection to Pinecone, Chroma, or pgvector does not need to be established until the first retrieval call. Wrap it in an `lru_cache`-decorated factory.
- **Load tools lazily in agents.** If an agent has many tools, only instantiate the tools that are actually needed for the current invocation. Use a registry that builds tools on demand.
- **A `RunnableLambda` wrapping a lazy factory is a lazy evaluation wrapper.** The lambda is not called until the chain is invoked, so the resources it accesses are also deferred.

---

## Example 1 — Lazy LLM initialisation

```python
from __future__ import annotations

import functools
from langchain_core.language_models import BaseChatModel


@functools.lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Return the shared LLM client.
    Constructed on first call; cached for the lifetime of the process.
    API credentials are read from environment variables at call time, not import time.
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model='gpt-4o-mini',
        temperature=0,
        max_retries=3,
        timeout=30,
    )


@functools.lru_cache(maxsize=1)
def get_strong_llm() -> BaseChatModel:
    """Separate lazy singleton for tasks requiring a more capable model."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model='gpt-4o', temperature=0)


# Chains call get_llm() — the first call constructs the client, all others return the cache
def build_summarise_chain():
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        ('system', 'Summarise in {max_sentences} sentences.'),
        ('human', '{text}'),
    ])
    return prompt | get_llm() | StrOutputParser()
```

```python
# WRONG — constructed at module load time
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini')   # ← runs at import time, always

# RIGHT — lazy
@functools.lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model='gpt-4o-mini')
```

---

## Example 2 — Lazy vector store connection

```python
from __future__ import annotations

import functools
from langchain_core.vectorstores import VectorStore


@functools.lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    """
    Connect to the vector store on first call.
    The connection is established lazily — only when retrieval is first needed.
    """
    from langchain_pinecone import PineconeVectorStore
    import os

    return PineconeVectorStore(
        index_name=os.environ['PINECONE_INDEX_NAME'],
        embedding=get_embeddings(),
    )


@functools.lru_cache(maxsize=1)
def get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model='text-embedding-3-small')


def build_retriever(k: int = 5):
    """Build a retriever backed by the lazily-connected vector store."""
    return get_vector_store().as_retriever(search_kwargs={'k': k})
```

---

## Example 3 — Lazy tool loading in an agent

Load tools on demand rather than at agent construction. This avoids initialising tools that are not needed for a given query.

```python
from __future__ import annotations

import functools
from langchain_core.tools import BaseTool


# Each tool factory is lazy — called only when the tool is actually registered
@functools.lru_cache(maxsize=1)
def get_search_tool() -> BaseTool:
    from langchain_community.tools.tavily_search import TavilySearchResults
    return TavilySearchResults(max_results=5)


@functools.lru_cache(maxsize=1)
def get_calculator_tool() -> BaseTool:
    from langchain_community.tools import Calculator
    return Calculator()


@functools.lru_cache(maxsize=1)
def get_code_tool() -> BaseTool:
    from langchain_experimental.tools import PythonREPLTool
    return PythonREPLTool()


# Tool registry — maps capability names to lazy factories
_TOOL_REGISTRY = {
    'search':     get_search_tool,
    'calculator': get_calculator_tool,
    'code':       get_code_tool,
}


def build_agent(required_tools: list[str]):
    """
    Build an agent with only the tools it needs.
    Tools are loaded lazily — only the requested ones are instantiated.
    """
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate

    tools = [_TOOL_REGISTRY[name]() for name in required_tools if name in _TOOL_REGISTRY]

    prompt = ChatPromptTemplate.from_messages([
        ('system', 'You are a helpful assistant.'),
        ('placeholder', '{chat_history}'),
        ('human', '{input}'),
        ('placeholder', '{agent_scratchpad}'),
    ])

    agent = create_tool_calling_agent(get_llm(), tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False)
```

---

## Example 4 — `RunnableLambda` as a lazy evaluation wrapper

A `RunnableLambda` defers evaluation of its function until the chain is invoked. Use this to wrap lazy factories that must not run until invocation time.

```python
from langchain_core.runnables import RunnableLambda


def lazy_retriever_step(input_data: dict) -> dict:
    """
    Retriever is accessed lazily here — get_vector_store() is not called
    until this step is executed during chain invocation.
    """
    query   = input_data['question']
    docs    = get_vector_store().similarity_search(query, k=5)
    context = '\n\n'.join(doc.page_content for doc in docs)
    return {**input_data, 'context': context}


rag_chain = (
    RunnableLambda(lazy_retriever_step)  # vector store accessed on invocation
    | prompt
    | get_llm()
    | StrOutputParser()
)
```

---

## Testing with Lazy Singletons

`lru_cache` caches across test runs if tests share a process. Clear the cache in tests that need a fresh instance.

```python
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def clear_llm_cache():
    """Clear the LLM cache before each test to allow injection of test doubles."""
    get_llm.cache_clear()
    get_vector_store.cache_clear()
    yield
    get_llm.cache_clear()
    get_vector_store.cache_clear()


def test_summarise_chain_with_fake_llm(clear_llm_cache):
    from langchain_core.language_models.fake_chat_models import FakeChatModel
    from langchain_core.messages import AIMessage

    fake = FakeChatModel(responses=[AIMessage(content='A one-sentence summary.')])

    with patch('myapp.chains.get_llm', return_value=fake):
        chain  = build_summarise_chain()
        result = chain.invoke({'text': 'Some text.', 'max_sentences': 1})

    assert result == 'A one-sentence summary.'
```

---

## Related Documents

- `global/gang-of-four.md` — Proxy section: the virtual proxy is one structural implementation of lazy loading; `lru_cache`-decorated factories are another mechanism for the same intent
