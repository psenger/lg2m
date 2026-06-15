# Secure Code Review — Python / LangChain

Guidelines for reviewing LangChain application code for security vulnerabilities. Based on the OWASP Secure Code Review Cheat Sheet with LLM-specific additions.

---

## Review Mindset

### Rules

- LLM applications have a unique attack surface: prompt injection, token leakage, model abuse.
- Review with an attacker's mindset — how could this code be abused?
- Focus on: prompt construction, input validation, API key handling, output validation, cost controls.
- Automated tools catch common Python issues; human review catches LLM-specific threats.

---

## Prompt Injection Prevention

### Checklist

- [ ] System prompts and user input are clearly separated in prompt templates.
- [ ] Raw user input is never concatenated into system prompts.
- [ ] User input is validated and sanitised before passing to chains.
- [ ] Output is validated to detect prompt leakage or manipulation.
- [ ] Tools have proper input validation — an LLM can be tricked into passing malicious tool arguments.
- [ ] Agent `max_iterations` is set to prevent infinite loops.

### Example

```python
# BAD — user input in system prompt
prompt = f"You are a helpful assistant. Context: {user_input}\nAnswer the question."

# GOOD — structured separation
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Follow these rules: {rules}"),
    ("human", "{user_input}"),  # Isolated in its own message
])
```

---

## API Key & Secrets Security

### Checklist

- [ ] No API keys hardcoded in source code or notebooks.
- [ ] API keys loaded from environment variables or secret managers.
- [ ] API keys never logged, never in error messages, never in responses.
- [ ] API keys never exposed to client-side code.
- [ ] `.env` files are gitignored. `.env.example` provided without real values.
- [ ] Key rotation policy in place.

---

## Input Validation

### Checklist

- [ ] All user inputs validated server-side (length, format, content type).
- [ ] Maximum input length enforced to prevent token budget abuse.
- [ ] File uploads validated by content type and size.
- [ ] SQL injection prevention: parameterised queries only.
- [ ] Error messages do not disclose internal details.

---

## LLM-Specific Security

### Checklist

- [ ] Rate limiting on inference endpoints to control costs and prevent abuse.
- [ ] Token budget limits per request and per user.
- [ ] Timeouts set on all LLM calls.
- [ ] Fallback chains defined for graceful degradation.
- [ ] Output length limits to prevent runaway generation.
- [ ] Model responses validated before being used in downstream operations (especially if feeding into SQL, commands, or file operations).
- [ ] No `pickle.loads()` on untrusted model files — use safe serialisation formats.
- [ ] Third-party models validated for integrity before use.

### Example

```python
# BAD — LLM output used directly in a query
sql = llm_response  # LLM could generate malicious SQL
db.execute(sql)

# GOOD — LLM output validated and parameterised
if not is_valid_sql_select(llm_response):
    raise SecurityError("Invalid query generated")
# Still use parameterised execution
```

---

## Authentication & Authorization

### Checklist

- [ ] All inference endpoints require authentication.
- [ ] Users can only access their own conversations/data (IDOR prevention).
- [ ] Admin functions (model management, config) properly protected.
- [ ] API key validation via dependency injection, not manual header parsing.

---

## Error Handling & Logging

### Checklist

- [ ] Generic error messages to clients — no stack traces or API keys in responses.
- [ ] LLM errors (rate limits, timeouts) mapped to appropriate HTTP status codes.
- [ ] All errors logged server-side with context.
- [ ] Sensitive data (API keys, user inputs with PII) redacted from logs.
- [ ] Token usage logged per request for cost monitoring.
- [ ] LangSmith tracing enabled for production debugging (not logging raw prompts with PII).

---

## Data Flow Analysis for LLM Apps

Trace data through the LLM pipeline:

1. **Sources**: User input, uploaded documents, retrieved context, conversation history.
2. **Processing**: Input validation → prompt assembly → LLM invocation → output parsing.
3. **Sinks**: API responses, database writes, tool invocations, file generation.
4. **Critical boundaries**:
   - User input → prompt template (injection risk)
   - LLM output → tool arguments (injection risk)
   - LLM output → database queries (injection risk)
   - LLM output → client response (leakage risk)

---

## Dependency & Model Security

### Checklist

- [ ] LangChain packages pinned to specific versions.
- [ ] Dependencies audited (`pip-audit`, `safety check`).
- [ ] No `pickle` deserialisation of untrusted model files.
- [ ] Third-party models verified for provenance and integrity.
- [ ] Model artifacts stored in access-controlled registries.

---

## Finding Severity Levels

| Severity | Description | Example |
|----------|-------------|---------|
| Critical | Immediately exploitable | Prompt injection leading to data exfil, API key exposure |
| High | Significant weakness | IDOR, unvalidated LLM output used in queries |
| Medium | Defence-in-depth gap | Missing rate limiting, no token budget |
| Low | Best practice violation | Missing security headers, verbose errors |
| Info | Observation | Deprecated LangChain API, code quality |
