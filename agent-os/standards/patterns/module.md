# Module Pattern — Python / LangChain

Organise LangChain components into cohesive packages with clear boundaries.

---

## Package Organisation

### Rules

- Group by component type: `prompts/`, `chains/`, `tools/`, `agents/`.
- Each file contains one primary component.
- Use `__init__.py` to define the public API for each package.
- Internal helpers stay unexported.

### Example

```
src/app/
├── prompts/
│   ├── __init__.py          # Exports: SUMMARIZE_PROMPT, RAG_PROMPT, CLASSIFY_PROMPT
│   ├── summarization.py     # SUMMARIZE_PROMPT
│   ├── rag.py               # RAG_PROMPT
│   └── classification.py    # CLASSIFY_PROMPT
├── chains/
│   ├── __init__.py          # Exports: create_summarize_chain, create_rag_chain
│   ├── summarize_chain.py
│   └── rag_chain.py
├── tools/
│   ├── __init__.py          # Exports: search_tool, calculator_tool
│   ├── search_tool.py
│   └── calculator_tool.py
```

```python
# prompts/__init__.py
from app.prompts.summarization import SUMMARIZE_PROMPT
from app.prompts.rag import RAG_PROMPT
from app.prompts.classification import CLASSIFY_PROMPT

__all__ = ["SUMMARIZE_PROMPT", "RAG_PROMPT", "CLASSIFY_PROMPT"]
```

```python
# chains/__init__.py
from app.chains.summarize_chain import create_summarize_chain
from app.chains.rag_chain import create_rag_chain

__all__ = ["create_summarize_chain", "create_rag_chain"]
```

---

## Encapsulation

### Rules

- Use `__all__` to explicitly declare what a package exports.
- Internal helpers (formatting functions, prompt fragments) are not exported.
- Other packages import from the package's `__init__.py`, never from internal files.

```python
# GOOD
from app.chains import create_rag_chain

# BAD — reaching into internal module
from app.chains.rag_chain import create_rag_chain, _format_context
```

---

## Prompt Module Pattern

### Rules

- Store prompts as module-level constants.
- Keep system prompts and user prompts in the same file for a given task.
- Export only the final `ChatPromptTemplate`, not raw prompt strings.

```python
# prompts/summarization.py
from langchain_core.prompts import ChatPromptTemplate

_SYSTEM = """You are a concise summarizer. Produce summaries with exactly
{max_sentences} sentences. Focus on key facts and actionable insights."""

_HUMAN = "Summarize this text:\n\n{text}"

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])
```
