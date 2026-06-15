# Circuit Breaker Pattern — Python / LangChain

> For the language-agnostic progressive enhancement philosophy behind this pattern, see `global/progressive-enhancement.md`. The Circuit Breaker is the implementation pattern for graceful degradation of external service calls. In LangChain applications the most critical boundary to protect is the LLM API itself. This document provides Python / LangChain-specific rules and examples.

A circuit breaker monitors calls to an external service and, after a threshold of failures, "opens" the circuit to stop sending requests. This prevents cascade failures and allows the failing service time to recover.

---

## States

| State | Behaviour |
|-------|-----------|
| **Closed** | Normal operation. Requests pass through to the LLM or external service. |
| **Open** | The service is failing. Requests are rejected immediately and the fallback chain is invoked. |
| **Half-Open** | Testing recovery. One request is allowed through. If it succeeds the circuit closes; if it fails the circuit reopens. |

---

## Rules

- The most important boundary to protect is the LLM API call itself — rate limits, token limits, and API outages all cause failures that must be handled gracefully.
- Use `.with_fallbacks([fallback_chain])` on Runnables as the LangChain-native mechanism for chain-level content and parsing failures.
- Use `.with_retry(stop_after_attempt=N, wait_exponential_jitter=True)` for transient errors before opening the circuit.
- Use `pybreaker` or equivalent at the HTTP client layer to protect against sustained outages.
- Always define a fallback chain that returns a safe default: an empty result, a cached response, or a simpler model.
- Never let an LLM API failure propagate as an unhandled exception to the user.
- Log state transitions for observability.

---

## Example — LangChain-Native Fallback and Retry

```python
# app/chains/resilient_chain.py
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer the question concisely."),
    ("human", "{question}"),
])


def create_resilient_chain(primary_llm: BaseChatModel, fallback_llm: BaseChatModel):
    """
    Returns a chain that retries transient failures then falls back to
    a simpler model if the primary is unavailable.
    """
    primary_chain = (
        PROMPT
        | primary_llm.with_retry(
            stop_after_attempt=3,
            wait_exponential_jitter=True,
        )
        | StrOutputParser()
    )

    fallback_chain = PROMPT | fallback_llm | StrOutputParser()

    # .with_fallbacks() catches exceptions from primary_chain and routes to fallback_chain
    return primary_chain.with_fallbacks([fallback_chain])
```

```python
# Usage — swap primary and fallback without changing the chain interface
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

chain = create_resilient_chain(
    primary_llm=ChatOpenAI(model="gpt-4o", timeout=10),
    fallback_llm=ChatAnthropic(model="claude-3-haiku-20240307"),
)

result = chain.invoke({"question": "What is the capital of France?"})
```

---

## Example — Static Fallback for Complete Outage

```python
# app/chains/safe_chain.py
from langchain_core.runnables import RunnableLambda
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def _static_fallback(_input: dict) -> str:
    return "I am temporarily unable to answer. Please try again shortly."


def create_safe_chain(llm: BaseChatModel):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the question concisely."),
        ("human", "{question}"),
    ])

    main_chain = prompt | llm | StrOutputParser()
    fallback = RunnableLambda(_static_fallback)

    return main_chain.with_fallbacks([fallback])
```

---

## Example — pybreaker at the HTTP Client Layer

```python
# app/adapters/llm_breaker.py
import logging
import pybreaker

logger = logging.getLogger(__name__)


class _LlmBreakerListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "LLM circuit breaker state change: %s -> %s (failures: %d)",
            old_state,
            new_state,
            cb.fail_counter,
        )


llm_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
    listeners=[_LlmBreakerListener()],
)
```

```python
# app/adapters/protected_llm_client.py
import pybreaker
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from app.adapters.llm_breaker import llm_breaker


class ProtectedLlmClient:
    """
    Wraps a LangChain BaseChatModel with a circuit breaker at the HTTP layer.
    Use this when you need infrastructure-level protection beyond what
    .with_fallbacks() provides (e.g. protecting shared rate-limit budgets).
    """

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def invoke(self, messages: list[BaseMessage]) -> str:
        try:
            response = llm_breaker.call(self._llm.invoke, messages)
            return response.content
        except pybreaker.CircuitBreakerError:
            logger.error("LLM circuit breaker is open — returning safe default")
            return "I am temporarily unavailable. Please try again shortly."
```

---

## Example — Complete Resilient Chain

```python
# app/chains/full_resilient_chain.py
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda


def create_full_resilient_chain(primary_llm: BaseChatModel, fallback_llm: BaseChatModel):
    """
    Full resilience stack:
      1. Retry transient errors (rate limits, timeouts) up to 3 times with backoff.
      2. Fall back to a cheaper model if the primary is persistently unavailable.
      3. Fall back to a static response if all models fail.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the question concisely."),
        ("human", "{question}"),
    ])

    primary = (
        prompt
        | primary_llm.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
        | StrOutputParser()
    )

    secondary = prompt | fallback_llm | StrOutputParser()

    static_fallback = RunnableLambda(
        lambda _: "I am temporarily unable to answer. Please try again shortly."
    )

    return primary.with_fallbacks([secondary, static_fallback])
```

---

## Related Documents

- `global/progressive-enhancement.md` — the philosophy of graceful degradation that motivates this pattern
- `global/hexagonal-architecture.md` — circuit breakers wrap driven ports (outbound adapters); the LLM API is a driven port
- `global/solid.md` — OCP: the circuit breaker wraps the LLM client without modifying it
