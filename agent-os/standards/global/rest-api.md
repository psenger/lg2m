# REST API Design — LangChain Services

Conventions for serving LangChain-powered applications via REST APIs using FastAPI.

---

## Framework

### Rules

- Use **FastAPI** as the primary web framework for LangChain services.
- Use **LangServe** for rapid chain deployment when appropriate.
- Prefer custom FastAPI routes for complex APIs with business logic.
- All LangChain endpoints must be `async` — use `ainvoke`, `astream`, `abatch`.

---

## Endpoint Design

### Rules

- Version the API: `/api/v1/...`.
- Use `POST` for LLM inference endpoints (they have request bodies and side effects).
- Use `GET` for retrieval/search endpoints when the query fits in URL params.
- Use Pydantic models for all request/response schemas.
- Set explicit timeouts on LLM calls — return `504` on timeout.
- Implement rate limiting on LLM endpoints to control costs.

### Example

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="LangChain API", version="1.0.0")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class ChatResponse(BaseModel):
    reply: str
    token_usage: dict | None = None

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await chat_chain.ainvoke({"message": request.message})
        return ChatResponse(reply=result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")
```

---

## Streaming with Server-Sent Events

### Rules

- Expose streaming endpoints for LLM responses using SSE.
- Use `astream` for simple token streaming.
- Use `astream_events` for fine-grained streaming with metadata.
- Set `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers.

### Example

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            async for chunk in chat_chain.astream({"message": request.message}):
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

---

## LangServe Integration

### Rules

- Use LangServe for rapid prototyping — it adds `/invoke`, `/stream`, `/batch` endpoints automatically.
- Prefer custom routes for production APIs with auth, rate limiting, and custom error handling.

```python
from langserve import add_routes

add_routes(app, chat_chain, path="/api/v1/chat", enabled_endpoints=["invoke", "stream"])
```

---

## Timeout Handling

```python
from asyncio import timeout

@app.post("/api/v1/chat")
async def chat_with_timeout(request: ChatRequest) -> ChatResponse:
    try:
        async with timeout(30):
            result = await chat_chain.ainvoke({"message": request.message})
            return ChatResponse(reply=result)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")
```

---

## Health Check

```python
@app.get("/health")
async def health():
    try:
        await llm.ainvoke("ping")
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

---

## API Key Security

### Rules

- Never expose LLM API keys to the client.
- Store API keys server-side in environment variables.
- Use FastAPI dependency injection for client authentication.
- Configure CORS explicitly — no wildcard origins in production.

---

## OWASP REST Security

### Rules

- **HTTPS only** — all endpoints must be served over HTTPS.
- **Sensitive IDs in URLs** — resource IDs in URL paths are logged by servers, proxies, and referrer headers, creating replay risks. Use opaque IDs (UUIDs). Never place API keys or tokens in URLs.
- **Security headers** — include `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` on all responses.
- **Input validation** — validate and sanitise all inputs. Reject oversized payloads with `413`.
- **Content type enforcement** — reject unexpected Content-Type headers with `415`.
- **Error handling** — generic error messages only. Never expose stack traces or internal details.
- **Rate limiting** — critical for LLM endpoints to control costs. Return `429` when exceeded.
- **Audit logging** — log security events. Sanitise log data.
- **JWT best practices** — verify `iss`, `aud`, `exp`, `nbf` claims if using JWT auth.
