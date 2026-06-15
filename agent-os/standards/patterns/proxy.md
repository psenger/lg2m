# Proxy Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Proxy section). This document provides Python / LangChain-specific implementation rules and examples.

Control access to LLMs and chains through caching, rate limiting, and fallback proxies.

---

## Caching Proxy

### Rules

- Cache LLM responses for identical inputs to reduce costs and latency.
- Use LangChain's built-in caching or wrap chains with a caching layer.
- Cache deterministic calls (temperature=0) aggressively; avoid caching creative responses.

### Example

```python
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache, InMemoryCache

# Global LLM cache
set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))

# Or in-memory for short-lived processes
set_llm_cache(InMemoryCache())

# Custom caching proxy at the chain level
class CachingChainProxy:
    """Proxy that caches chain results by input hash."""

    def __init__(self, chain: Runnable, cache: Cache, ttl: int = 3600):
        self.chain = chain
        self.cache = cache
        self.ttl = ttl

    async def ainvoke(self, input_data: dict, **kwargs) -> str:
        cache_key = self._hash_input(input_data)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        result = await self.chain.ainvoke(input_data, **kwargs)
        await self.cache.set(cache_key, result, self.ttl)
        return result

    @staticmethod
    def _hash_input(data: dict) -> str:
        import hashlib, json
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
```

---

## Fallback Proxy (RunnableWithFallbacks)

### Rules

- Use `chain.with_fallbacks([...])` to define fallback chains when the primary fails.
- Common pattern: expensive model → cheaper model → static response.
- Fallbacks trigger on any exception from the primary chain.

### Example

```python
# Primary: GPT-4o, Fallback: GPT-3.5-turbo, Final fallback: static
primary_chain = prompt | ChatOpenAI(model="gpt-4o") | StrOutputParser()
fallback_chain = prompt | ChatOpenAI(model="gpt-3.5-turbo") | StrOutputParser()
static_fallback = RunnableLambda(lambda x: "I'm temporarily unable to process this request.")

resilient_chain = primary_chain.with_fallbacks(
    [fallback_chain, static_fallback],
    exceptions_to_handle=(Exception,),
)
```

---

## Rate-Limiting Proxy

### Rules

- Wrap LLM calls with rate limiting to control costs and stay within API limits.
- Track calls per time window.
- Raise a clear error when limits are exceeded.

### Example

```python
import time
from collections import deque

class RateLimitedLLMProxy:
    """Proxy that rate-limits LLM invocations."""

    def __init__(self, llm: BaseChatModel, max_per_minute: int = 60):
        self.llm = llm
        self.max_per_minute = max_per_minute
        self.timestamps: deque[float] = deque()

    async def ainvoke(self, input_data, **kwargs):
        now = time.time()
        # Remove timestamps older than 1 minute
        while self.timestamps and now - self.timestamps[0] > 60:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.max_per_minute:
            wait_time = 60 - (now - self.timestamps[0])
            raise RuntimeError(f"Rate limit reached. Try again in {wait_time:.1f}s")

        self.timestamps.append(now)
        return await self.llm.ainvoke(input_data, **kwargs)
```

---

## Token Budget Proxy

```python
class TokenBudgetProxy:
    """Proxy that tracks and limits total token usage."""

    def __init__(self, chain: Runnable, max_tokens: int = 100_000):
        self.chain = chain
        self.max_tokens = max_tokens
        self.total_tokens = 0
        self.counter = TokenCounterHandler()

    async def ainvoke(self, input_data: dict, **kwargs) -> str:
        if self.total_tokens >= self.max_tokens:
            raise RuntimeError(f"Token budget exhausted: {self.total_tokens}/{self.max_tokens}")

        result = await self.chain.ainvoke(
            input_data,
            config={"callbacks": [self.counter]},
        )
        self.total_tokens = self.counter.total_tokens
        return result
```
