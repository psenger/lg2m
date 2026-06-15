# Dependency Injection — Python / LangChain

Inject LLMs, retrievers, and services into chains and tools rather than hardcoding them. This is the practical implementation of the Dependency Inversion Principle (see `global/solid.md`) and hexagonal architecture (see `global/hexagonal-architecture.md`) applied to agentic pipelines. `BaseChatModel`, `BaseRetriever`, and custom tool protocols are ports; `ChatAnthropic`, `PGVectorRetriever`, and concrete tool implementations are adapters. Chain factories accept ports — never concrete adapters. The composition root (startup module or app factory) wires in real adapters; tests pass fakes.

---

## Chain Factory Injection

### Rules

- Chain factories accept `BaseChatModel`, `BaseRetriever`, etc. as parameters.
- Never instantiate `ChatOpenAI()` inside a chain definition.
- Wire everything in a composition root or app startup module.

### Example

```python
# chains/rag_chain.py — depends on abstractions
from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnablePassthrough

def create_rag_chain(
    llm: BaseChatModel,
    retriever: BaseRetriever,
) -> Runnable[str, str]:
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

# app/startup.py — composition root
from app.config.settings import get_settings
from app.services.llm_service import create_llm
from app.services.vector_store import create_retriever

settings = get_settings()
llm = create_llm(settings)
retriever = create_retriever(settings)
rag_chain = create_rag_chain(llm, retriever)
```

---

## RunnableConfig for Runtime Injection

### Rules

- Use `RunnableConfig` to pass runtime configuration (callbacks, metadata, tags) without changing the chain signature.
- Use `configurable_fields` for runtime-swappable chain components.

### Example

```python
from langchain_core.runnables import ConfigurableField

# Make the LLM swappable at runtime
configurable_chain = (
    prompt
    | ChatOpenAI(model="gpt-4o").configurable_fields(
        model_name=ConfigurableField(id="llm_model", name="Model"),
        temperature=ConfigurableField(id="llm_temp", name="Temperature"),
    )
    | StrOutputParser()
)

# Override at invocation time
result = await configurable_chain.ainvoke(
    {"question": "Hello"},
    config={"configurable": {"llm_model": "gpt-3.5-turbo", "llm_temp": 0.0}},
)
```

---

## Tool Dependency Injection

### Rules

- Use closures or factory functions to inject dependencies into tools.
- Tools should not import global singletons.

```python
def create_search_tool(search_client: SearchClient) -> BaseTool:
    @tool
    def search_documents(query: str) -> str:
        """Search the document store for relevant information."""
        results = search_client.search(query, max_results=5)
        return "\n".join(r.snippet for r in results)

    return search_documents

# Wire in startup
search_tool = create_search_tool(search_client)
agent = create_research_agent(llm, tools=[search_tool, calculator_tool])
```

---

## FastAPI Dependency Injection

### Rules

- Use FastAPI's `Depends` to inject chains and services into route handlers — do not import module-level singletons directly.
- Define a `get_*` provider function per dependency; FastAPI caches per-request by default.
- Override providers in tests using `app.dependency_overrides` — do not patch module globals.

```python
from fastapi import Depends

def get_chain() -> Runnable:
    """FastAPI dependency that provides the configured chain."""
    return rag_chain

@app.post("/api/v1/ask")
async def ask(
    request: AskRequest,
    chain: Runnable = Depends(get_chain),
):
    result = await chain.ainvoke(request.question)
    return {"answer": result}

# In tests — override the dependency, do not patch the module
def get_fake_chain() -> Runnable:
    return FakeChatModel(responses=[AIMessage(content="test answer")]) | StrOutputParser()

app.dependency_overrides[get_chain] = get_fake_chain
```

---

## Related Documents

- `global/hexagonal-architecture.md` — `BaseChatModel` and `BaseRetriever` are ports; concrete LLM clients and vector stores are adapters; startup is the composition root
- `global/solid.md` — Dependency Inversion Principle (D) is why chain factories accept base classes not concrete clients
- `global/gang-of-four.md` — Factory Method is the pattern behind chain factory functions; Strategy is why swapping `BaseChatModel` implementations works without changing chain logic
- `standards/testing/mocking.md` — `FakeChatModel` and mock retrievers as port-boundary substitutes in unit tests
