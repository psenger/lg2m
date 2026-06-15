# Flyweight Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and the intrinsic/extrinsic state distinction, see `global/gang-of-four.md` (Flyweight section). This document provides Python / LangChain-specific rules and examples.

Share fine-grained objects to avoid recreating expensive, immutable state for every use. In LangChain applications, the most common flyweights are LLM clients, embedding models, prompt templates, and tokenisers — objects that are costly to initialise and safe to share across many chain invocations.

---

## Rules

- **Shared LangChain objects must be immutable (or treated as immutable).** LLM clients, embedding models, and prompt templates carry no per-request state. Do not modify them after construction.
- **Use a module-level registry or `functools.lru_cache` as the flyweight factory.** Construct the object once; return the cached instance on every subsequent call.
- **The expensive construction happens once — during application startup or on first use.** LLM client initialisation involves loading credentials, building HTTP connection pools, and sometimes loading model weights. None of this should happen per request.
- **Extrinsic state (the actual input/prompt/query) is passed at invocation time, not stored on the flyweight.** The prompt template is the flyweight; the variables filled into the template are the extrinsic state.
- **In tests, a `FakeChatModel` instance can be a flyweight.** When multiple tests use the same response sequence, a single `FakeChatModel` instance shared across those tests avoids unnecessary construction.

---

## Example 1 — Shared prompt templates

A `ChatPromptTemplate` parses the template string, validates placeholders, and constructs a message factory at build time. This work need not be repeated for every chain invocation. The template is the flyweight; the variable values are the extrinsic state.

```python
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

# Intrinsic state: the template structure (immutable after construction)
# Extrinsic state: the dict of variables passed to .invoke() or .format_messages()


# Module-level flyweights — constructed once
SUMMARISE_PROMPT = ChatPromptTemplate.from_messages([
    ('system', 'Summarise the following text in {max_sentences} sentences.'),
    ('human', '{text}'),
])

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ('system', 'Classify the following text into one of: {categories}. Respond with the category name only.'),
    ('human', '{text}'),
])

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ('system', 'Extract the following fields from the text: {fields}. Return as JSON.'),
    ('human', '{text}'),
])


# Chain uses the shared prompt — no reconstruction per invocation
def build_summarise_chain(llm):
    from langchain_core.output_parsers import StrOutputParser
    return SUMMARISE_PROMPT | llm | StrOutputParser()
```

---

## Example 2 — Shared embedding model

Initialising an embedding model involves loading model weights or building an API client. Share a single instance across all chains that need embeddings.

```python
from __future__ import annotations

import functools
from langchain_core.embeddings import Embeddings


@functools.lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """
    Return the shared embedding model instance.
    Constructed once; subsequent calls return the cached instance.
    lru_cache(maxsize=1) means one instance is retained for the lifetime of the process.
    """
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model='text-embedding-3-small')


# Any module that needs embeddings calls get_embeddings()
# The model is constructed exactly once regardless of how many callers there are.

def build_vector_store(documents):
    from langchain_community.vectorstores import FAISS
    return FAISS.from_documents(documents, get_embeddings())


def build_retriever(vector_store):
    return vector_store.as_retriever(search_kwargs={'k': 5})
```

---

## Example 3 — Shared LLM client

```python
from __future__ import annotations

import functools
from langchain_core.language_models import BaseChatModel


@functools.lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Return the shared LLM client.
    HTTP connection pool, credentials, and retry configuration
    are set up once and reused across all chain invocations.
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
    """Separate flyweight for tasks requiring a stronger model."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model='gpt-4o', temperature=0)


# Chains receive the shared LLM — they do not construct it
def build_classification_chain():
    from langchain_core.output_parsers import StrOutputParser
    return CLASSIFY_PROMPT | get_llm() | StrOutputParser()
```

---

## Example 4 — Shared tokeniser

```python
from __future__ import annotations

import functools


@functools.lru_cache(maxsize=None)
def get_tokenizer(model_name: str):
    """
    Return a cached tokeniser for the given model.
    Tokeniser loading is expensive (reads a vocabulary file).
    lru_cache keyed by model_name handles multiple model variants.
    The model_name is the intrinsic key; the text to tokenise is the extrinsic state.
    """
    import tiktoken
    return tiktoken.encoding_for_model(model_name)


def count_tokens(text: str, model: str = 'gpt-4o-mini') -> int:
    """Count tokens using a shared tokeniser. text is extrinsic state."""
    enc = get_tokenizer(model)
    return len(enc.encode(text))
```

---

## Example 5 — FakeChatModel as a test flyweight

When tests use the same fixed response sequence, share a single `FakeChatModel` instance rather than constructing one per test.

```python
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage


@pytest.fixture(scope='module')
def fake_summarise_llm():
    """
    Module-scoped flyweight: one FakeChatModel for all summarisation tests.
    Constructed once; shared across all tests in the module.
    """
    from langchain_core.language_models.fake_chat_models import FakeChatModel
    return FakeChatModel(responses=[
        AIMessage(content='This is a summary.'),
        AIMessage(content='Another summary.'),
    ])


def test_summarise_short_text(fake_summarise_llm):
    chain = build_summarise_chain(fake_summarise_llm)
    result = chain.invoke({'text': 'Some text.', 'max_sentences': 1})
    assert result == 'This is a summary.'


def test_summarise_long_text(fake_summarise_llm):
    chain = build_summarise_chain(fake_summarise_llm)
    result = chain.invoke({'text': 'Another longer text.', 'max_sentences': 2})
    assert result == 'Another summary.'
```

---

## Related Documents

- `global/gang-of-four.md` — Flyweight section for the language-agnostic pattern; also see the Singleton section for comparison
