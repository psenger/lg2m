# Observer Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Observer section). This document provides Python / LangChain-specific implementation rules and examples.

LangChain's callback system is a built-in observer pattern for monitoring chain execution.

---

## LangChain Callbacks

### Rules

- Use callbacks for cross-cutting concerns: logging, tracing, metrics, token counting.
- Never put observability logic inside chain steps — use callback handlers.
- Use `BaseCallbackHandler` for sync handlers, `AsyncCallbackHandler` for async.
- Pass callbacks via `config={"callbacks": [...]}` or set globally.
- Use LangSmith for production tracing — it uses the callback system under the hood.

### Example

```python
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
import logging

logger = logging.getLogger(__name__)

class LoggingCallbackHandler(BaseCallbackHandler):
    """Log chain and LLM events."""

    def on_chain_start(self, serialized, inputs, **kwargs):
        chain_name = serialized.get("name", "unknown")
        logger.info("Chain started: %s", chain_name)

    def on_chain_end(self, outputs, **kwargs):
        logger.info("Chain completed")

    def on_chain_error(self, error, **kwargs):
        logger.error("Chain failed: %s", error)

    def on_llm_start(self, serialized, prompts, **kwargs):
        logger.debug("LLM call started with %d prompts", len(prompts))

    def on_llm_end(self, response: LLMResult, **kwargs):
        usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        logger.info("LLM completed, tokens: %s", usage)

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "unknown")
        logger.info("Tool started: %s", tool_name)

    def on_tool_end(self, output, **kwargs):
        logger.info("Tool completed")

# Usage
result = await chain.ainvoke(
    {"question": "What is LCEL?"},
    config={"callbacks": [LoggingCallbackHandler()]},
)
```

---

## Token Counting Handler

```python
class TokenCounterHandler(BaseCallbackHandler):
    """Track token usage across chain execution."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs):
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            self.total_input_tokens += usage.get("prompt_tokens", 0)
            self.total_output_tokens += usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

# Usage
counter = TokenCounterHandler()
result = await chain.ainvoke(input_data, config={"callbacks": [counter]})
logger.info("Total tokens used: %d", counter.total_tokens)
```

---

## LangSmith Tracing

### Rules

- Enable LangSmith tracing in non-local environments for production observability.
- Set environment variables: `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_TRACING=true`.
- Use `@traceable` decorator for custom functions you want traced alongside chains.

```python
from langsmith import traceable

@traceable(name="process_document")
async def process_document(text: str) -> dict:
    summary = await summarize_chain.ainvoke({"text": text})
    classification = await classify_chain.ainvoke({"text": text})
    return {"summary": summary, "classification": classification}
```

---

## Custom Event System

For application-level events beyond LangChain's callback scope:

```python
from collections import defaultdict
from typing import Callable

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def emit(self, event: str, **kwargs) -> None:
        for handler in self._handlers[event]:
            handler(**kwargs)

# Usage
event_bus = EventBus()
event_bus.on("chain.completed", lambda result, tokens: log_metrics(result, tokens))
```
