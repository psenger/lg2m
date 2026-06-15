# Method Chaining — Python / LangChain

Method chaining in LangChain applications is primarily expressed through the LangChain Expression Language (LCEL) pipe operator (`|`) and the Runnable composition methods (`.pipe()`, `.with_config()`, `.with_fallbacks()`, `.with_retry()`). These operators are the LangChain-idiomatic way to compose chains and should be preferred over manual method chaining for chain construction.

---

## Rules

- **Prefer `|` and `.pipe()` over manual method chaining for chain composition.** LCEL's pipe operator is the intended API for building chains. It composes `Runnable` objects and produces a new `Runnable` — immutable, inspectable, and traceable.
- **Use `.with_config()` to layer runtime configuration onto a chain without modifying it.** Tags, run names, callbacks, and recursion limits are all runtime config that belongs on the chain, not in the chain's logic.
- **Use `.with_fallbacks()` to express progressive enhancement at the chain level.** Define a primary chain and one or more fallback chains. LangChain will try each in order on failure.
- **Use `.with_retry()` to add retry logic to a chain step without modifying the step.** Retry configuration is operational concern, not business logic.
- **Terminal operations are `invoke()`, `ainvoke()`, `stream()`, and `astream()`.** These are the terminal methods of the LCEL chain — they trigger actual execution.

---

## Example 1 — Building a chain with LCEL pipe operators

The `|` operator chains Runnable objects. Each step's output becomes the next step's input. This is LCEL method chaining.

```python
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)

# Each | returns a new RunnableSequence — immutable, composable
summarise_chain = (
    ChatPromptTemplate.from_messages([
        ('system', 'Summarise the following text in {max_sentences} sentences.'),
        ('human', '{text}'),
    ])
    | llm
    | StrOutputParser()
)

# Invoke is the terminal method
result = summarise_chain.invoke({'text': 'Some long text...', 'max_sentences': 2})
```

---

## Example 2 — Composing chain configuration with method chaining

`.with_config()`, `.with_fallbacks()`, and `.with_retry()` each return new `Runnable` objects — they are immutable chaining methods on the Runnable protocol.

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def build_robust_summarise_chain() -> Runnable:
    """
    Build a chain with:
    - A named run for tracing
    - Retry on transient failures
    - A fallback to a different LLM if the primary fails repeatedly
    """
    prompt = ChatPromptTemplate.from_messages([
        ('system', 'Summarise the following text in {max_sentences} sentences.'),
        ('human', '{text}'),
    ])

    primary_llm   = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    fallback_llm  = ChatAnthropic(model='claude-haiku-20240307', temperature=0)

    # Build the primary chain with retry and named config
    primary_chain = (
        prompt
        | primary_llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
        | StrOutputParser()
    ).with_config(run_name='SummariseChain', tags=['summarise'])

    # Build the fallback chain
    fallback_chain = (
        prompt
        | fallback_llm
        | StrOutputParser()
    ).with_config(run_name='SummariseChainFallback')

    # Wire fallback — primary is tried first; fallback activates on failure
    return primary_chain.with_fallbacks([fallback_chain])
```

---

## Example 3 — Step-by-step chain construction using `.pipe()`

`.pipe()` is the explicit method-chaining alternative to `|`. Use it when you need to programmatically compose a chain (e.g. adding steps conditionally).

```python
from __future__ import annotations

from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def build_rag_chain(
    retriever,
    llm,
    *,
    include_sources: bool = False,
) -> Runnable:
    """
    Build a RAG chain step by step using .pipe().
    Conditional steps are added based on configuration.
    """
    prompt = ChatPromptTemplate.from_messages([
        ('system', 'Answer based on the context below.\n\nContext:\n{context}'),
        ('human', '{question}'),
    ])

    def format_docs(docs) -> str:
        return '\n\n'.join(doc.page_content for doc in docs)

    # Build the chain step by step
    chain = (
        RunnablePassthrough.assign(context=retriever | RunnableLambda(format_docs))
        .pipe(prompt)
        .pipe(llm)
        .pipe(StrOutputParser())
    )

    if include_sources:
        # Conditionally extend the chain to also return source documents
        def add_sources(result: str) -> dict:
            return {'answer': result, 'sources': []}  # sources attached earlier in a full impl

        chain = chain.pipe(RunnableLambda(add_sources))

    return chain.with_config(run_name='RagChain')
```

---

## Example 4 — Immutable chain variants from a base

Each `.with_config()` call returns a new Runnable. The original is unchanged. Use this to create named variants from a shared base chain.

```python
from langchain_core.callbacks import BaseCallbackHandler

# Base chain — shared
base_chain = summarise_chain

# Named variant for production (with tracing callbacks)
prod_chain = base_chain.with_config(
    run_name='SummariseProd',
    tags=['prod', 'summarise'],
    callbacks=[langsmith_callback],
)

# Variant for testing (no callbacks, deterministic)
test_chain = base_chain.with_config(
    run_name='SummariseTest',
    tags=['test'],
)

# Both base_chain, prod_chain, and test_chain are independent Runnables.
# Modifying one does not affect the others.
```

---

## Related Documents

- `global/gang-of-four.md` — Builder section for the language-agnostic pattern; LCEL chains are a specialised form of the Builder pattern applied to Runnable composition
