# AI/ML Security — Python / LangChain

Security guidance for operating and deploying LangChain and LLM-powered applications. Based on OWASP Secure AI/ML Model Ops Cheat Sheet.

---

## Common Threats

| Threat | Description |
|--------|-------------|
| Prompt Injection | Malicious input that overrides or hijacks LLM behaviour |
| Data Poisoning | Injecting malicious data into training/fine-tuning datasets |
| Model Extraction | Reconstructing model parameters via inference queries |
| Adversarial Input | Crafted inputs that mislead model predictions |
| Token/Key Leakage | Exposing API keys in code, logs, or client-side responses |
| Unsecured Endpoints | Inference APIs lacking auth, rate limiting, or validation |

---

## Prompt Injection Prevention

### Rules

- Use structured prompt templates that clearly separate system instructions from user input.
- Never concatenate raw user input into system prompts.
- Validate and sanitise user input before passing to LLM chains.
- Use output validation to detect when the LLM has been manipulated.
- Monitor for anomalous outputs that don't match expected patterns.

### Example

```python
# BAD — user input concatenated into system prompt
prompt = f"You are a helpful assistant. {user_input}"

# GOOD — structured template with clear separation
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Follow these rules strictly:\n{rules}"),
    ("human", "{user_input}"),  # User input is isolated
])

# Additional: validate output doesn't contain leaked system prompts
def validate_output(output: str, system_prompt: str) -> str:
    if system_prompt[:50] in output:
        raise SecurityError("Possible prompt leakage detected")
    return output
```

---

## API Key and Secrets Management

### Rules

- Never hardcode API keys in source code or notebooks.
- Use environment variables or secret managers (AWS Secrets Manager, HashiCorp Vault).
- Never log API keys or include them in error messages.
- Never expose LLM API keys to client-side code.
- Rotate keys regularly.
- Use `.env.example` as a template — never commit `.env`.

---

## Inference API Security

### Rules

- Apply authentication and authorization on all inference endpoints.
- Validate and sanitise all inputs (max length, allowed characters, content type).
- Implement rate limiting to prevent abuse and control costs.
- Set request size limits — reject oversized payloads with `413`.
- Set explicit timeouts on LLM calls.
- Log requests with traceability but avoid logging sensitive content.

---

## Model and Artifact Security

### Rules

- Store models in access-controlled registries.
- Validate third-party models before use — verify integrity and provenance.
- Encrypt model weights and datasets at rest.
- Sign model binaries with digital signatures.
- Never deserialise untrusted `.pkl` or `.pt` files — they can execute arbitrary code.

---

## Monitoring and Drift Detection

### Rules

- Monitor input distribution, output entropy, and latency.
- Detect model drift via statistical analysis.
- Alert on unusual usage patterns (scraping, injection attempts, abnormal token usage).
- Use LangSmith or equivalent for production tracing and debugging.
- Log token usage per request for cost monitoring.

---

## Adversarial Robustness

### Rules

- Include adversarial examples in testing.
- Monitor model confidence thresholds to identify out-of-distribution inputs.
- Use shadow deployments to evaluate model behaviour on real inputs without affecting production.
- Use canary releases for gradual rollout with rapid rollback capability.

---

## Incident Response

### Rules

- Define escalation procedures for model abuse or drift.
- Implement rollback mechanisms for model deployments.
- Maintain an inventory of deployed models and their versions.
- Remove orphaned test/staging models from production environments.
