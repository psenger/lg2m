# Coding Conventions — Python / LangChain

Project structure, imports, configuration, and naming conventions for LangChain applications.

---

## Project Structure

```
project/
├── pyproject.toml
├── .env.example
├── src/
│   └── app/
│       ├── __init__.py
│       ├── config/
│       │   └── settings.py          # pydantic-settings
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── summarization.py     # Prompt templates
│       │   └── classification.py
│       ├── chains/
│       │   ├── __init__.py
│       │   ├── summarize_chain.py
│       │   └── rag_chain.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── search_tool.py
│       │   └── calculator_tool.py
│       ├── agents/
│       │   ├── __init__.py
│       │   └── research_agent.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── schemas.py           # Pydantic models
│       ├── services/
│       │   ├── __init__.py
│       │   ├── llm_service.py       # LLM factory
│       │   └── vector_store.py
│       └── api/
│           ├── __init__.py
│           ├── app.py               # FastAPI app
│           └── routes/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── scripts/
    └── ingest.py
```

### Rules

- One major component per file: one chain, one tool, one agent.
- Name files after the component: `summarize_chain.py`, `search_tool.py`.
- Group by component type, not by feature.
- Prompts, chains, tools, and agents each get their own package.

---

## Import Conventions

### Rules

- Import from specific LangChain packages, not the umbrella `langchain` package.
- Order: standard library → third-party → langchain packages → local application.

```python
# GOOD — specific package imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import FAISS

# BAD — umbrella imports (deprecated paths)
# from langchain.chat_models import ChatOpenAI
# from langchain.embeddings import OpenAIEmbeddings
```

---

## Configuration with pydantic-settings

### Rules

- Use `pydantic-settings` for all configuration.
- Never hardcode API keys, model names, or endpoint URLs.
- Prefix environment variables by service.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM
    openai_api_key: str = Field(..., description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o")
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # Vector Store
    pinecone_api_key: str = Field(default="")
    pinecone_index_name: str = Field(default="default-index")

    # Observability
    langsmith_api_key: str = Field(default="")
    langsmith_project: str = Field(default="default")
    langsmith_tracing: bool = Field(default=False)

def get_settings() -> Settings:
    return Settings()
```

---

## Pydantic Models for Structured Output

### Rules

- Use Pydantic v2 models for all structured input/output.
- Use `Field` with `description` — LLMs read these descriptions for structured output.
- Keep models in a `models/schemas.py` module.

```python
from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    """Result of a text classification."""
    category: str = Field(description="The predicted category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(description="Brief explanation")
```

---

## Async Convention

### Rules

- Default to async: `ainvoke`, `astream`, `abatch`.
- Only use sync methods in scripts or CLI tools.
- Use `asyncio.gather` for parallel chain execution.

---

## Dependencies

### Rules

- Pin LangChain package versions in `pyproject.toml`.
- Use separate dependency groups for dev, test, and production.
- Keep `langchain-core` version consistent across all `langchain-*` packages.
