# SOLID Principles — Python / LangChain

> For the language-agnostic principles and theory, see `global/solid.md` from the default profile. This document extends those principles with Python / LangChain-specific rules and examples.

SOLID principles applied to LangChain-based AI applications.

---

## S — Single Responsibility Principle

Each component should have one reason to change.

### Rules

- Each chain does one task (summarise, classify, extract — not all at once).
- Prompts live in their own module, separate from chain logic.
- Tools do one thing — a search tool searches; it doesn't also format results.
- Keep LLM configuration separate from chain composition.
- Agents orchestrate tools; they don't contain business logic.

### Example

```python
# BAD — one chain does everything
chain = prompt | llm | parse | save_to_db | send_email

# GOOD — separate chains composed at the orchestration layer
summarize_chain = summarize_prompt | llm | StrOutputParser()
classify_chain = classify_prompt | llm | PydanticOutputParser(pydantic_object=Classification)

# Orchestrator composes them
async def process_document(text: str) -> ProcessedDocument:
    summary, classification = await asyncio.gather(
        summarize_chain.ainvoke({"text": text}),
        classify_chain.ainvoke({"text": text}),
    )
    return ProcessedDocument(summary=summary, classification=classification)
```

---

## O — Open/Closed Principle

Add new capabilities by adding new components, not modifying existing ones.

### Rules

- Add new tools to agents without modifying the agent definition.
- Add new chain variants without modifying existing chains.
- Use LCEL's pipe operator to extend behaviour.
- Use RunnableBranch for conditional routing without changing existing branches.

### Example

```python
# Adding a new output format without modifying existing chains
def create_output_chain(format: str) -> Runnable:
    """Factory that returns the right output chain — new formats don't touch existing code."""
    chains = {
        "json": prompt | llm | JsonOutputParser(),
        "text": prompt | llm | StrOutputParser(),
        "pydantic": prompt | llm | PydanticOutputParser(pydantic_object=Result),
    }
    if format not in chains:
        raise ValueError(f"Unknown format: {format}")
    return chains[format]
```

---

## L — Liskov Substitution Principle

Any Runnable can replace another Runnable with the same input/output types.

### Rules

- All LangChain components implement the `Runnable` interface — they are substitutable.
- Custom runnables must honour the `invoke`/`ainvoke`/`stream`/`astream` contract.
- When swapping LLMs (OpenAI → Anthropic), the chain should work identically.
- Test with `FakeLLM` / `FakeChatModel` — they are substitutable for real LLMs.

### Example

```python
from langchain_core.language_models import BaseChatModel

def create_summarize_chain(llm: BaseChatModel) -> Runnable[dict, str]:
    """Works with any BaseChatModel — OpenAI, Anthropic, local models."""
    return SUMMARIZE_PROMPT | llm | StrOutputParser()

# All of these work
chain_openai = create_summarize_chain(ChatOpenAI(model="gpt-4o"))
chain_anthropic = create_summarize_chain(ChatAnthropic(model="claude-sonnet-4-20250514"))
chain_test = create_summarize_chain(FakeChatModel(responses=["Test summary"]))
```

---

## I — Interface Segregation Principle

Depend on the narrowest interface that satisfies your needs.

### Rules

- Type chain parameters as `BaseChatModel`, not `ChatOpenAI`.
- Type retrievers as `BaseRetriever`, not `FAISSRetriever`.
- Type embeddings as `Embeddings`, not `OpenAIEmbeddings`.
- Import from `langchain_core`, not provider-specific packages, for base types.

### Example

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.embeddings import Embeddings

def create_rag_chain(
    llm: BaseChatModel,        # not ChatOpenAI
    retriever: BaseRetriever,  # not FAISSRetriever
) -> Runnable[str, str]:
    return (
        {"context": retriever, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
        | StrOutputParser()
    )
```

---

## D — Dependency Inversion Principle

Chain factories depend on abstractions, not concrete LLM providers.

### Rules

- Never import `ChatOpenAI` inside a chain definition — accept `BaseChatModel` as a parameter.
- Create LLM instances in a composition root or factory module.
- Configuration (model name, temperature, API keys) lives in settings, not in chain code.

### Example

```python
# services/llm_service.py — composition root for LLMs
from app.config.settings import get_settings

def create_llm() -> BaseChatModel:
    settings = get_settings()
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.llm_model, temperature=settings.llm_temperature)
    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.llm_model, temperature=settings.llm_temperature)
    raise ValueError(f"Unknown provider: {settings.llm_provider}")

# chains/summarize.py — depends on abstraction
def create_summarize_chain(llm: BaseChatModel) -> Runnable[dict, str]:
    return SUMMARIZE_PROMPT | llm | StrOutputParser()
```
