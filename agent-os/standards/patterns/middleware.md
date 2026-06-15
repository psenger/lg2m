# Middleware Pattern — Python / LangChain

> The middleware chain is an implementation of the GoF Chain of Responsibility pattern — see `global/gang-of-four.md` (Chain of Responsibility section) for the language-agnostic description. This document covers the Python / LangChain-specific mechanics.

Intercept and transform chain execution at defined points using callbacks and runnable wrappers.

---

## Callbacks as Middleware

### Rules

- LangChain callbacks are the primary middleware mechanism — they intercept chain, LLM, and tool execution.
- Use callbacks for logging, metrics, token counting, and tracing.
- Callbacks are transparent — chains don't know they're being observed.

### Example

```python
from langchain_core.callbacks import BaseCallbackHandler

class RateLimitMiddleware(BaseCallbackHandler):
    """Middleware that tracks and enforces rate limits on LLM calls."""

    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.call_timestamps: list[float] = []

    def on_llm_start(self, serialized, prompts, **kwargs):
        import time
        now = time.time()
        # Remove timestamps older than 1 minute
        self.call_timestamps = [t for t in self.call_timestamps if now - t < 60]
        if len(self.call_timestamps) >= self.max_calls:
            raise RuntimeError(f"Rate limit exceeded: {self.max_calls} calls/minute")
        self.call_timestamps.append(now)

# Usage
result = await chain.ainvoke(
    input_data,
    config={"callbacks": [RateLimitMiddleware(max_calls_per_minute=30)]},
)
```

---

## Input/Output Transformation Middleware

### Rules

- Use `RunnableLambda` to create middleware that transforms data between chain steps.
- Place transformation middleware at chain boundaries (input preprocessing, output postprocessing).

### Example

```python
from langchain_core.runnables import RunnableLambda

# Input sanitization middleware
def sanitize_input(data: dict) -> dict:
    """Strip and normalise text inputs."""
    return {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}

# Output truncation middleware
def truncate_output(text: str, max_length: int = 5000) -> str:
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

# Compose as middleware
chain = (
    RunnableLambda(sanitize_input)   # Input middleware
    | prompt
    | llm
    | StrOutputParser()
    | RunnableLambda(lambda t: truncate_output(t, 2000))  # Output middleware
)
```

---

## Request Context Middleware

```python
import uuid
from langchain_core.runnables import RunnableConfig

def add_request_context(data: dict) -> dict:
    """Add a unique request ID for tracing."""
    return {**data, "_request_id": str(uuid.uuid4())}

chain_with_context = (
    RunnableLambda(add_request_context)
    | prompt
    | llm
    | StrOutputParser()
)
```
