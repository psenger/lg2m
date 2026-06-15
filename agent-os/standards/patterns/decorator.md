# Decorator Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Decorator section). This document provides Python / LangChain-specific implementation rules and examples.

Extend chain and tool behaviour without modifying their source code.

---

## The @tool Decorator

### Rules

- Use `@tool` to convert plain functions into LangChain tools.
- Always provide a docstring — the LLM reads it to understand when and how to use the tool.
- Use type hints and Pydantic `Field` for argument descriptions.

### Example

```python
from langchain_core.tools import tool
from pydantic import Field

@tool
def search_knowledge_base(
    query: str = Field(description="The search query to find relevant documents"),
    max_results: int = Field(default=5, description="Maximum number of results to return"),
) -> str:
    """Search the internal knowledge base for documents matching the query.

    Use this tool when the user asks about company policies, procedures, or internal documentation.
    """
    results = vector_store.similarity_search(query, k=max_results)
    return "\n\n".join(doc.page_content for doc in results)
```

---

## Custom Retry Decorator

### Rules

- Wrap chain invocations with retry logic for transient LLM API failures.
- Use exponential backoff.
- Only retry on retryable errors (rate limits, timeouts), not on validation errors.

### Example

```python
import functools
import asyncio
import logging
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)

def retry_on_llm_error(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator for LLM chain invocations."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except OutputParserException:
                    raise  # Don't retry parse errors
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs",
                            fn.__name__, attempt, max_attempts, e, delay,
                        )
                        await asyncio.sleep(delay)
            raise last_error
        return wrapper
    return decorator

@retry_on_llm_error(max_attempts=3, base_delay=2.0)
async def summarize_document(text: str) -> str:
    return await summarize_chain.ainvoke({"text": text})
```

---

## Logging Decorator for Chains

```python
def with_logging(chain: Runnable, name: str) -> Runnable:
    """Wrap a chain with input/output logging."""
    async def log_and_run(input_data):
        logger.info("Chain '%s' started", name)
        result = await chain.ainvoke(input_data)
        logger.info("Chain '%s' completed", name)
        return result

    return RunnableLambda(log_and_run)

logged_chain = with_logging(summarize_chain, "summarize")
```

---

## Validation Decorator

```python
def validate_input(schema: type[BaseModel]):
    """Decorator to validate chain input against a Pydantic schema."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(input_data: dict, **kwargs):
            validated = schema(**input_data)
            return await fn(validated.model_dump(), **kwargs)
        return wrapper
    return decorator

class SummarizeInput(BaseModel):
    text: str = Field(min_length=10)
    max_sentences: int = Field(default=3, ge=1, le=20)

@validate_input(SummarizeInput)
async def summarize(input_data: dict) -> str:
    return await summarize_chain.ainvoke(input_data)
```
