# Error Handling — Python / LangChain

Comprehensive error handling for LLM-powered applications: API errors, token limits, rate limiting, parsing failures, and chain recovery.

---

## LLM API Errors

### Rules

- Catch and categorise LLM API errors: authentication, rate limiting, token limits, server errors.
- Map API errors to appropriate HTTP status codes when serving via FastAPI.
- Log full error details server-side; return sanitised messages to clients.

### Example

```python
import logging
from openai import (
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Base class for LLM-related errors."""
    status_code: int = 502

class LLMAuthError(LLMError):
    status_code = 500  # Server config issue, not client's fault

class LLMRateLimitError(LLMError):
    status_code = 429

class LLMTokenLimitError(LLMError):
    status_code = 422

class LLMTimeoutError(LLMError):
    status_code = 504

async def safe_chain_invoke(chain, input_data: dict) -> str:
    """Invoke a chain with comprehensive error handling."""
    try:
        return await chain.ainvoke(input_data)
    except AuthenticationError as e:
        logger.error("LLM authentication failed: %s", e)
        raise LLMAuthError("LLM service configuration error") from e
    except RateLimitError as e:
        logger.warning("LLM rate limit hit: %s", e)
        raise LLMRateLimitError("LLM rate limit exceeded. Try again later.") from e
    except APITimeoutError as e:
        logger.warning("LLM request timed out: %s", e)
        raise LLMTimeoutError("LLM request timed out") from e
    except APIConnectionError as e:
        logger.error("LLM connection error: %s", e)
        raise LLMError("Unable to connect to LLM service") from e
    except OutputParserException as e:
        logger.warning("LLM output parsing failed: %s", e)
        raise LLMError(f"Failed to parse LLM response: {e}") from e
    except Exception as e:
        logger.error("Unexpected LLM error: %s", e, exc_info=True)
        raise LLMError("An unexpected error occurred") from e
```

---

## Token Limit Handling

### Rules

- Estimate input tokens before sending to the LLM.
- Truncate or chunk long inputs proactively.
- Handle `context_length_exceeded` errors with a fallback strategy.

### Example

```python
def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters."""
    return len(text) // 4

def truncate_for_context(text: str, max_tokens: int = 3000) -> str:
    """Truncate text to fit within token budget."""
    max_chars = max_tokens * 4
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[Truncated due to length]"
    return text

# For long documents, chunk and process separately
async def process_long_document(text: str, chain: Runnable) -> list[str]:
    """Process a long document by chunking."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)
    chunks = splitter.split_text(text)
    results = await chain.abatch([{"text": chunk} for chunk in chunks])
    return results
```

---

## Output Parsing Errors

### Rules

- LLM output is non-deterministic — always handle parsing failures.
- Use `OutputFixingParser` for automatic repair.
- Log the raw LLM output for debugging when parsing fails.
- Set a maximum number of fix attempts to avoid infinite loops.

```python
from langchain.output_parsers import OutputFixingParser
from langchain_core.output_parsers import PydanticOutputParser

base_parser = PydanticOutputParser(pydantic_object=AnalysisResult)
fixing_parser = OutputFixingParser.from_llm(parser=base_parser, llm=llm, max_retries=2)

async def parse_with_logging(raw_output: str) -> AnalysisResult:
    try:
        return base_parser.parse(raw_output)
    except OutputParserException:
        logger.warning("Parse failed, attempting auto-fix. Raw output: %s", raw_output[:500])
        return await fixing_parser.aparse(raw_output)
```

---

## Chain Failure Recovery

### Rules

- Use `with_fallbacks()` for chain-level recovery.
- Use `with_retry()` for transient error recovery.
- Combine both for maximum resilience.

```python
from langchain_core.runnables import RunnableConfig

# Retry on transient errors, then fall back
resilient_chain = (
    primary_chain
    .with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
        retry_if_exception_type=(APIConnectionError, APITimeoutError, RateLimitError),
    )
    .with_fallbacks([
        fallback_chain,
        RunnableLambda(lambda x: "Service temporarily unavailable."),
    ])
)
```

---

## FastAPI Error Handlers

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.exception_handler(LLMError)
async def handle_llm_error(request, error: LLMError):
    return JSONResponse(
        status_code=error.status_code,
        content={"errors": [{"code": type(error).__name__, "message": str(error)}]},
    )
```

---

## Logging with Callbacks

### Rules

- Use LangChain callbacks for structured logging of chain execution.
- Use LangSmith for production tracing and debugging.
- Include chain name, input preview, duration, and token usage in logs.

```python
class ErrorLoggingHandler(BaseCallbackHandler):
    def on_chain_error(self, error, **kwargs):
        logger.error("Chain error: %s", error, exc_info=True)

    def on_llm_error(self, error, **kwargs):
        logger.error("LLM error: %s", error)

    def on_tool_error(self, error, **kwargs):
        logger.error("Tool error: %s", error)
```

---

## Graceful Degradation Strategy

| Failure | Recovery |
|---------|----------|
| Primary LLM down | Fall back to secondary model |
| Token limit exceeded | Truncate input, retry |
| Output parse failure | Auto-fix with OutputFixingParser |
| Rate limit hit | Exponential backoff, then queue |
| All LLMs unavailable | Return cached response or static message |
| Vector store unavailable | Skip RAG, use LLM knowledge only |
