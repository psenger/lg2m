# Error-First Pattern — Python / LangChain

Graceful degradation, fallback chains, and explicit error handling for LLM-powered applications.

---

## RunnableWithFallbacks

### Rules

- Use `chain.with_fallbacks([...])` for automatic recovery from LLM failures.
- Order fallbacks from most capable to least capable.
- Always include a static fallback as the last resort.

### Example

```python
primary = prompt | ChatOpenAI(model="gpt-4o") | StrOutputParser()
fallback = prompt | ChatOpenAI(model="gpt-3.5-turbo") | StrOutputParser()
static = RunnableLambda(lambda x: "Unable to process request. Please try again later.")

resilient_chain = primary.with_fallbacks([fallback, static])
```

---

## Output Parser Error Recovery

### Rules

- LLM output may not match expected formats — handle `OutputParserException`.
- Use `OutputFixingParser` to auto-fix malformed output by re-prompting the LLM.
- Use `RetryOutputParser` for retry with the original prompt plus error context.

### Example

```python
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import OutputFixingParser, RetryWithErrorOutputParser

base_parser = PydanticOutputParser(pydantic_object=ExtractionResult)

# Auto-fix: sends malformed output back to LLM with format instructions
fixing_parser = OutputFixingParser.from_llm(parser=base_parser, llm=llm)

# Retry: includes the original prompt for full context
retry_parser = RetryWithErrorOutputParser.from_llm(parser=base_parser, llm=llm)

# Use fixing_parser in chain
chain = prompt | llm | fixing_parser
```

---

## Result Pattern for Chain Outputs

### Rules

- Wrap chain invocations in a Result type for explicit error handling at the application layer.

### Example

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Ok:
    value: object

@dataclass(frozen=True)
class Err:
    error: str
    error_type: str = "unknown"

async def safe_invoke(chain: Runnable, input_data: dict) -> Ok | Err:
    """Invoke a chain with explicit error handling."""
    try:
        result = await chain.ainvoke(input_data)
        return Ok(value=result)
    except OutputParserException as e:
        return Err(error=str(e), error_type="parse_error")
    except Exception as e:
        return Err(error=str(e), error_type="chain_error")

# Usage
result = await safe_invoke(extraction_chain, {"text": document})
match result:
    case Ok(value=data):
        return {"data": data}
    case Err(error=msg, error_type="parse_error"):
        return {"error": f"Failed to parse LLM output: {msg}"}, 422
    case Err(error=msg):
        return {"error": msg}, 502
```

---

## Retry Logic

### Rules

- Retry on transient errors (rate limits, timeouts, network issues).
- Do not retry on validation or parsing errors — they will fail again.
- Use exponential backoff.

```python
import asyncio

async def invoke_with_retry(
    chain: Runnable,
    input_data: dict,
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> str:
    for attempt in range(1, max_attempts + 1):
        try:
            return await chain.ainvoke(input_data)
        except OutputParserException:
            raise  # Don't retry parse errors
        except Exception as e:
            if attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("Attempt %d/%d failed: %s. Retrying in %.1fs", attempt, max_attempts, e, delay)
            await asyncio.sleep(delay)
```

---

## Token Limit Handling

### Rules

- Check input token count before sending to the LLM.
- Truncate or chunk long inputs rather than letting them fail.
- Handle `context_length_exceeded` errors gracefully.

```python
from langchain_core.runnables import RunnableLambda

def truncate_to_token_limit(text: str, max_tokens: int = 3000) -> str:
    """Rough truncation based on character estimate (4 chars ≈ 1 token)."""
    max_chars = max_tokens * 4
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[Text truncated due to length]"
    return text

chain = (
    RunnableLambda(lambda x: {**x, "text": truncate_to_token_limit(x["text"])})
    | prompt
    | llm
    | StrOutputParser()
)
```
