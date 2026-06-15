# Standards for Foundation Layer

Full text of each standard selected for this spec (see `agent-os/standards/`). These are the working agreements for the IR + parsing foundation; the architecture group is a forward constraint (keep this layer free of any framework import).

---

## global/value-objects

# Value Objects

A Value Object is an object whose identity is defined entirely by its value, not by a reference or database ID. Two value objects with the same data are interchangeable. They are always immutable. They eliminate Primitive Obsession — the code smell of using raw strings, integers, and floats to represent domain concepts.

---

## What Is a Value Object

### Rules

- A Value Object has no identity beyond its value. Two Money objects of £10.00 GBP are equal; it does not matter which one you use.
- Value Objects are always immutable. Operations that would "change" a Value Object return a new instance.
- Value Objects encapsulate validation. An Email object cannot represent an invalid email — the constructor enforces the invariant.
- Value Objects carry domain semantics. `Money(10.00, 'GBP')` communicates more than `float 10.0`.
- Value Objects should define equality based on their contents, not their reference.

### Example

```
WITHOUT value objects — Primitive Obsession:
  function transfer(fromAccount, toAccount, amount: float, currency: string)

  transfer(account1, account2, 100.0, 'GBP')   ← nothing prevents:
  transfer(account1, account2, 'GBP', 100.0)   ← swapped params, compiles, wrong
  transfer(account1, account2, -50.0, 'GBP')   ← negative amount, no validation

WITH value objects:
  function transfer(fromAccount, toAccount, amount: Money)

  money = Money(100.0, Currency.GBP)            ← validated at construction
  transfer(account1, account2, money)           ← param order enforced by type
```

---

## When to Introduce a Value Object

### Rules

- When a primitive has validation rules (email format, positive amounts, non-empty names).
- When a primitive carries units or constraints that must be enforced everywhere it is used.
- When the same primitive appears together with another in multiple places (street + city + postcode → Address).
- When code is littered with validation of the same raw primitive in multiple locations.
- When a function takes two or more primitives of the same type that could be accidentally swapped.

### Primitive Obsession Signals

```
SIGNALS — consider a Value Object:
  function setAge(age: int)                             ← can pass negative or 200
  function createUser(email: string)                    ← can pass any string
  function charge(amount: float, currency: string)      ← units and currency coupled
  if len(name) > 0 and '@' in email and ...            ← validation duplicated across codebase
```

---

## Value Object vs Entity

- **Entity**: has an identity independent of its values. Two Users with the same name are not the same User — they have different IDs. Entities are mutable over time.
- **Value Object**: has no identity beyond its value. Two Money(10, GBP) instances are interchangeable. Value Objects are immutable.

```
Entity:   User(id=1, name='Alice')  ≠  User(id=2, name='Alice')   ← different identity
Value:    Money(10, GBP)            =  Money(10, GBP)              ← same value, interchangeable
```

---

## Immutability and Operations

### Rules

- Operations on a Value Object return a new instance — never mutate the original.
- This makes Value Objects safe to share, cache, and use as dictionary keys.

### Example

```
money = Money(100, 'GBP')
discounted = money.subtract(Money(10, 'GBP'))   ← returns new Money(90, 'GBP')
# money is still Money(100, 'GBP')
```

---

## Related Documents

- `global/dry.md` — Value Objects eliminate duplicated validation logic (single authoritative representation of the constraint)
- `global/solid.md` — SRP: each Value Object is responsible for the validity and behaviour of one domain concept
- `global/gang-of-four.md` — Flyweight: immutable Value Objects are natural candidates for flyweight sharing

---

## global/simplicity

# Simplicity

Simplicity is an active discipline, not the absence of effort. The simplest solution that works is almost always the best one. Complexity is the primary cost in software — it makes code harder to read, test, change, and delete.

---

## YAGNI — You Aren't Gonna Need It

Do not add functionality until it is needed. Build what the current requirement demands, not what you imagine future requirements might demand.

### Rules

- Do not add parameters, configuration options, or extension points that no current caller uses.
- Do not abstract prematurely. Two lines of similar code is not a problem. An unnecessary abstraction is.
- Do not write code for hypothetical future requirements. Requirements change; speculative code becomes wrong code that must be maintained or deleted.
- Every line of code is a liability: it must be read, understood, tested, and maintained. Code that does not exist has no cost.
- When you genuinely need the feature, add it then — it will be informed by real requirements and real context.

### Example

```
WRONG — speculative extensibility no caller uses:
  function createUser(data, options = {
    notificationChannel: 'email',
    auditLog: true,
    retryOnFailure: false,
    ... 8 more options nobody asked for
  })

RIGHT — build what is needed now:
  function createUser(data)
  # add options when a real requirement demands them
```

---

## KISS — Keep It Simple

Prefer the simplest solution that correctly solves the problem. Do not introduce accidental complexity.

### Rules

- Choose boring technology when it solves the problem. Reach for a complex solution only when a simpler one is demonstrably insufficient.
- Flat is better than nested. A function with three levels of nesting is a candidate for extraction.
- Direct is better than clever. Code that requires a comment to explain what it does is more complex than code that does not.
- The simplest data structure that works is the right one. A plain list is better than a custom tree if a list solves the problem.
- If you cannot explain the solution to a colleague in two sentences, it may be too complex.

### Example

```
WRONG — clever, fragile, hard to follow:
  result = data.reduce((acc, x) => ({...acc, [x.id]: [...(acc[x.id] || []), x]}), {})

RIGHT — direct, readable:
  grouped = {}
  for item in data:
    if item.id not in grouped:
      grouped[item.id] = []
    grouped[item.id].append(item)
```

---

## Kent Beck's Four Rules of Simple Design

In priority order — higher rules take precedence over lower ones.

1. **Passes the tests** — The code must do what is required. No other rule matters if this one is not met.
2. **Reveals intention** — The code communicates its purpose through names, structure, and flow. A reader should understand what the code does without needing to run it.
3. **No duplication** — Every piece of knowledge has a single authoritative representation. (See `global/dry.md`.)
4. **Fewest elements** — Given the above constraints, remove every class, function, variable, and parameter that is not necessary. Fewer elements means less to understand, test, and maintain.

### Rules

- Apply the Four Rules in order. A cleverly minimal solution that fails tests or obscures intent violates a higher rule.
- "Reveals intention" is the rule most often violated by AI-generated code — ask: does this name, structure, and abstraction communicate what it does and why?
- "Fewest elements" is not about line count. A well-named ten-line function with one clear purpose has fewer elements than a three-line function that requires three comments to understand.
- Run the Four Rules as a checklist after each TDD cycle — they are the refactoring criterion.

### Example

```
After GREEN — evaluate with the Four Rules:

1. Passes tests?          → yes
2. Reveals intention?     → does getUsersByStatus(status) clearly say what it does? yes
3. No duplication?        → is the status-filter logic copied elsewhere? no
4. Fewest elements?       → is there a parameter, variable, or method that can be removed?
                            → the `tempList` variable is unnecessary — filter directly
```

---

## Related Documents

- `global/dry.md` — Rule 3 (No duplication) in depth
- `global/tdd-workflow.md` — the TDD cycle is where the Four Rules are applied
- `global/solid.md` — SOLID principles are specific applications of these broader simplicity rules
- `global/gang-of-four.md` — patterns solve recurring problems; YAGNI says do not apply a pattern until the problem is actually present

---

## global/clean-code

# Clean Code Conventions — Python / LangChain

Write clear, maintainable LangChain code. Name things well, keep chains readable, and document intent.

---

## Naming

### Rules

- Use `snake_case` for variables, functions, and modules.
- Use `PascalCase` for classes and Pydantic models.
- Use `UPPER_SNAKE_CASE` for prompt template constants.
- Suffix LangChain components by type: `_chain`, `_agent`, `_tool`, `_retriever`, `_prompt`, `_parser`.
- Name chain factories as `create_<purpose>_chain`.
- Name tools with action verbs: `search_web`, `calculate_cost`, `fetch_document`.

### Example

```python
# BAD
llm_thing = ChatOpenAI()
p = ChatPromptTemplate.from_messages([...])
c = p | llm_thing | StrOutputParser()

# GOOD
chat_llm = ChatOpenAI(model="gpt-4o")
SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([...])
summarize_chain = SUMMARIZE_PROMPT | chat_llm | StrOutputParser()
```

---

## Chain Readability

### Rules

- Use LCEL pipe syntax for chain composition — it reads top-to-bottom.
- Break long chains across multiple lines with each step on its own line.
- Add comments above non-obvious chain steps.
- Extract complex sub-chains into named variables before composing.

### Example

```python
# BAD — unreadable single line
chain = ChatPromptTemplate.from_messages([("system", "..."), ("human", "{q}")]) | ChatOpenAI(model="gpt-4o", temperature=0) | StrOutputParser()

# GOOD — each step on its own line
rag_chain = (
    # Retrieve context and pass question through
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    # Format the prompt with context and question
    | rag_prompt
    # Generate response
    | llm
    # Parse to string
    | StrOutputParser()
)
```

---

## Comments and Docstrings

### Rules

- Document chain factories with docstrings explaining input/output types.
- Use `# TODO(PROJ-123):` with ticket references for planned work.
- Reference the ticket number when a change is tied to a task: `# PROJ-456: Added fallback for token limit errors`.
- Use `# FIXME(PROJ-789):` for known issues.
- Comment *why* a chain step exists when it's not obvious.
- Document prompt templates with their expected variables.

### Example

```python
def create_extraction_chain(llm: BaseChatModel) -> Runnable[dict, ExtractionResult]:
    """Create a chain that extracts structured entities from text.

    Input: {"text": str}
    Output: ExtractionResult with entities list.
    """
    return EXTRACTION_PROMPT | llm | PydanticOutputParser(pydantic_object=ExtractionResult)

# PROJ-234: Temperature set to 0 for deterministic extraction
extraction_llm = ChatOpenAI(model="gpt-4o", temperature=0)
```

---

## Prompt Organisation

### Rules

- Store prompts in a dedicated `prompts/` module.
- Define prompts as module-level constants in `UPPER_SNAKE_CASE`.
- Use `ChatPromptTemplate.from_messages()` for chat prompts.
- Keep system prompts separate from user prompts.
- Never hardcode prompts inline in chain definitions.

```python
# prompts/summarization.py
from langchain_core.prompts import ChatPromptTemplate

SUMMARIZE_SYSTEM = """You are a precise summarizer. Summarize the given text
in {max_sentences} sentences. Focus on key facts and conclusions."""

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUMMARIZE_SYSTEM),
    ("human", "Summarize this text:\n\n{text}"),
])
```

---

## Type Safety

### Rules

- Type all chain factory return values as `Runnable[InputType, OutputType]`.
- Use Pydantic `BaseModel` for all structured inputs and outputs.
- Use `Field` with `description` for tool arguments — LLMs read these descriptions.
- Run `mypy` or `pyright` in CI.

---

## global/coding-conventions

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

---

## testing/testing

# Testing Standards — Python / LangChain

Testing strategies for LangChain applications: unit testing chains with mocked LLMs, integration testing, and LLM output evaluation.

---

## Test Framework

### Rules

- Use **pytest** with **pytest-asyncio** for async chain testing.
- Use **pytest-mock** for mocking.
- Use LangChain's `FakeLLM` / `FakeChatModel` for deterministic unit tests.
- Use `pytest-cov` for coverage reporting.

---

## Unit Testing Chains with Mocked LLMs

### Rules

- Use `FakeChatModel` or `FakeListLLM` to return predetermined responses.
- Unit tests must be fast, deterministic, and cost nothing (no real API calls).
- Test chain logic, not LLM intelligence.
- Verify that prompts are formatted correctly and parsers extract expected fields.

### Example

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

from app.chains.summarize_chain import create_summarize_chain

@pytest.fixture
def fake_llm():
    return FakeChatModel(responses=[
        AIMessage(content="This is a test summary of the document."),
    ])

class TestSummarizeChain:
    @pytest.mark.asyncio
    async def test_returns_summary_string(self, fake_llm):
        chain = create_summarize_chain(fake_llm)

        result = await chain.ainvoke({
            "text": "Long document content here...",
            "max_sentences": 3,
        })

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_passes_text_to_prompt(self, fake_llm):
        chain = create_summarize_chain(fake_llm)

        await chain.ainvoke({"text": "Test input", "max_sentences": 2})

        # Verify the LLM received the formatted prompt
        last_call = fake_llm.calls[-1] if hasattr(fake_llm, 'calls') else None
        # Assertions on prompt content
```

---

## Testing Structured Output

```python
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage
from app.models.schemas import ClassificationResult

@pytest.mark.asyncio
async def test_classification_chain_parses_output():
    # Arrange — fake LLM returns valid JSON
    fake_response = AIMessage(content='{"category": "tech", "confidence": 0.95, "reasoning": "Contains technical terms"}')
    fake_llm = FakeChatModel(responses=[fake_response])
    chain = create_classification_chain(fake_llm)

    # Act
    result = await chain.ainvoke({"text": "Python is a programming language"})

    # Assert
    assert isinstance(result, ClassificationResult)
    assert result.category == "tech"
    assert result.confidence == 0.95
```

---

## Testing Tools

### Rules

- Test tools as plain functions — they are just Python functions with metadata.
- Mock external services the tool depends on.
- Test both success and error paths.

```python
from app.tools.search_tool import create_search_tool

class TestSearchTool:
    def test_returns_formatted_results(self, mocker):
        mock_client = mocker.MagicMock()
        mock_client.search.return_value = [
            mocker.MagicMock(snippet="Result 1"),
            mocker.MagicMock(snippet="Result 2"),
        ]
        tool = create_search_tool(mock_client)

        result = tool.invoke("test query")

        assert "Result 1" in result
        assert "Result 2" in result
        mock_client.search.assert_called_once_with("test query", max_results=5)

    def test_handles_empty_results(self, mocker):
        mock_client = mocker.MagicMock()
        mock_client.search.return_value = []
        tool = create_search_tool(mock_client)

        result = tool.invoke("obscure query")

        assert result == "" or "no results" in result.lower()
```

---

## Fixtures for LangChain

```python
# tests/conftest.py
import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

@pytest.fixture
def fake_llm():
    """A fake LLM that returns a default response."""
    return FakeChatModel(responses=[AIMessage(content="Default test response")])

@pytest.fixture
def fake_llm_factory():
    """Factory for creating fake LLMs with specific responses."""
    def _create(*responses: str):
        return FakeChatModel(responses=[AIMessage(content=r) for r in responses])
    return _create

@pytest.fixture
def mock_retriever(mocker):
    """A mock retriever that returns empty results."""
    from langchain_core.documents import Document
    retriever = mocker.MagicMock()
    retriever.invoke.return_value = []
    retriever.ainvoke.return_value = []
    return retriever
```

---

## Integration Tests with Real LLMs

### Rules

- Mark integration tests with `@pytest.mark.integration` and skip by default.
- Run integration tests in CI on a schedule, not on every push.
- Set a budget cap for integration test API costs.
- Use the cheapest model that validates the behaviour.

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_summarize_chain_with_real_llm():
    """Integration test — calls a real LLM. Requires OPENAI_API_KEY."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    chain = create_summarize_chain(llm)

    result = await chain.ainvoke({
        "text": "Python is a high-level programming language. It was created by Guido van Rossum.",
        "max_sentences": 1,
    })

    assert isinstance(result, str)
    assert len(result) > 10
    assert len(result) < 500
```

---

## Testing Async Chains

```python
@pytest.mark.asyncio
async def test_parallel_chain_execution(fake_llm_factory):
    llm = fake_llm_factory("Summary result", "Classification result")
    summary_chain = create_summarize_chain(llm)
    classify_chain = create_classification_chain(llm)

    import asyncio
    summary, classification = await asyncio.gather(
        summary_chain.ainvoke({"text": "test"}),
        classify_chain.ainvoke({"text": "test"}),
    )

    assert summary is not None
    assert classification is not None
```

---

## Coverage

### Rules

- Aim for 80%+ coverage on chain factories, tools, and service logic.
- Do not count integration tests toward coverage thresholds.
- Test error paths: what happens when the LLM returns garbage, times out, or rate limits.

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80 -m 'not integration'"
markers = ["integration: marks tests that call real LLM APIs (deselect with '-m not integration')"]

[tool.pytest-asyncio]
mode = "auto"
```

---

## testing/mocking

# Mocking Standards — Python / LangChain

Mock at system boundaries only. In LangChain projects the most important boundary is the LLM itself — unit tests must never call real LLM APIs. Use deterministic fakes for all LLM interactions.

These rules follow from hexagonal architecture (ports and adapters) and orthogonal design. The application core (chains, agents, use-case logic) depends on port interfaces such as `BaseChatModel` and `BaseRetriever`; concrete LLM clients and retriever implementations are adapters. Tests replace those adapters with fakes (`FakeChatModel`, mock retrievers) at the port interface level. See `global/hexagonal-architecture.md` for the foundational principles.

---

## What to Mock

### Rules

- Always mock the LLM port (`BaseChatModel`) in unit tests — use `FakeChatModel` or `FakeListLLM`. Real API calls are slow, costly, non-deterministic, and belong only in integration tests.
- Mock driven ports that reach the outside world: search APIs, databases, HTTP clients, message queues, retrievers.
- Do not mock your own chains, agents, or internal collaborators — if the test becomes painful without mocking internals, the components are not orthogonal and the design needs fixing, not the test.
- Mock at the port (interface) boundary: if your code depends on `BaseChatModel`, pass in `FakeChatModel` — do not patch the Anthropic or OpenAI client (the adapter) directly.
- Never let a concrete LLM client type (`ChatAnthropic`, `ChatOpenAI`) appear in core logic — that couples the core to an adapter and violates hexagonal architecture.
- Use `mocker` from `pytest-mock` — it automatically resets mocks after each test.

---

## FakeChatModel — LLM Unit Tests

### Rules

- Use `FakeChatModel` for chat models (`ChatAnthropic`, `ChatOpenAI`, etc.).
- Pass a list of `AIMessage` responses in the order they will be consumed.
- Test chain logic, parser behaviour, and prompt formatting — not LLM intelligence.
- Do not assert on the exact content of responses unless your test is specifically about parsing.

### Example

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage
from app.chains.summarize_chain import create_summarize_chain

@pytest.fixture
def fake_llm():
    return FakeChatModel(responses=[
        AIMessage(content='This is a deterministic test summary.'),
    ])

class TestSummarizeChain:
    @pytest.mark.asyncio
    async def test_returns_non_empty_string(self, fake_llm):
        chain = create_summarize_chain(fake_llm)
        result = await chain.ainvoke({'text': 'Long document...', 'max_sentences': 2})
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_structured_output_is_parsed_correctly(self):
        fake = FakeChatModel(responses=[
            AIMessage(content='{"category": "tech", "confidence": 0.95}'),
        ])
        chain = create_classification_chain(fake)
        result = await chain.ainvoke({'text': 'Python is a programming language'})
        assert result.category == 'tech'
        assert result.confidence == 0.95
```

---

## FakeListLLM — Completion Model Tests

### Rules

- Use `FakeListLLM` for non-chat completion models.
- Each call to the LLM consumes the next response in the list in order.

### Example

```python
from langchain_community.llms.fake import FakeListLLM
from app.chains.legacy_chain import create_legacy_chain

def test_legacy_chain_formats_output():
    llm = FakeListLLM(responses=['Formatted output text'])
    chain = create_legacy_chain(llm)
    result = chain.invoke({'input': 'test prompt'})
    assert 'Formatted output text' in result
```

---

## Fake LLM Fixtures — Shared conftest.py

### Rules

- Define reusable fake LLM fixtures in `conftest.py`.
- Provide a factory fixture when tests need different response sequences.

### Example

```python
# tests/conftest.py
import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

@pytest.fixture
def fake_llm():
    """Default fake LLM returning a generic response."""
    return FakeChatModel(responses=[AIMessage(content='Default test response')])

@pytest.fixture
def fake_llm_factory():
    """Factory for creating fake LLMs with specific response sequences."""
    def _make(*responses: str) -> FakeChatModel:
        return FakeChatModel(responses=[AIMessage(content=r) for r in responses])
    return _make

@pytest.fixture
def mock_retriever(mocker):
    """Fake retriever returning no documents by default."""
    from langchain_core.documents import Document
    retriever = mocker.MagicMock()
    retriever.invoke.return_value = []
    retriever.ainvoke.return_value = []
    return retriever
```

---

## Mocking Tools

### Rules

- Test tools as plain Python functions — they are just functions with metadata attached.
- Mock the external client the tool depends on, not the tool itself.
- Test both the success path and error/empty-result paths.

### Example

```python
from app.tools.search_tool import create_search_tool

class TestSearchTool:
    def test_returns_formatted_results(self, mocker):
        mock_client = mocker.MagicMock()
        mock_client.search.return_value = [
            mocker.MagicMock(snippet='Result 1'),
            mocker.MagicMock(snippet='Result 2'),
        ]
        tool = create_search_tool(mock_client)

        result = tool.invoke('test query')

        assert 'Result 1' in result
        assert 'Result 2' in result
        mock_client.search.assert_called_once_with('test query', max_results=5)

    def test_handles_empty_results_gracefully(self, mocker):
        mock_client = mocker.MagicMock()
        mock_client.search.return_value = []
        tool = create_search_tool(mock_client)

        result = tool.invoke('obscure query with no results')

        assert result == '' or 'no results' in result.lower()
```

---

## SDK-Style Interfaces — Design for Mockability

### Rules

- Define one method per external operation. Each specific method is independently mockable.
- Depend on `BaseChatModel` in your chain factories — never import `ChatAnthropic` or `ChatOpenAI` directly into business logic. This lets you pass `FakeChatModel` in tests.

### Example

```python
# BAD — hard-coded to a specific LLM, cannot mock without patching
from langchain_anthropic import ChatAnthropic

def create_chain():
    llm = ChatAnthropic(model='claude-sonnet-4-6-20250514')
    return prompt | llm | parser

# GOOD — accepts BaseChatModel, FakeChatModel works as a drop-in
from langchain_core.language_models import BaseChatModel

def create_chain(llm: BaseChatModel):
    return prompt | llm | parser

# In tests
chain = create_chain(FakeChatModel(responses=[AIMessage(content='test')]))
```

---

## Integration Tests with Real LLMs

### Rules

- Mark all tests that call real LLM APIs with `@pytest.mark.integration`.
- Skip integration tests by default in CI — run on a schedule or on demand.
- Use the cheapest model that validates the behaviour.
- Never assert on exact LLM output text in integration tests — assert on structure and type only.

### Example

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chain_returns_structured_output_with_real_llm():
    from langchain_anthropic import ChatAnthropic
    llm = ChatAnthropic(model='claude-haiku-4-5-20251001', temperature=0)
    chain = create_classification_chain(llm)

    result = await chain.ainvoke({'text': 'Python is a programming language'})

    # Assert structure only — not exact content
    assert hasattr(result, 'category')
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
```

---

## global/hexagonal-architecture

# Hexagonal Architecture and Orthogonal Design

These two principles are the architectural foundation behind the "mock at system boundaries only" rule. Understanding them explains *why* the testing and mocking standards are written the way they are — not just *what* to do.

---

## Orthogonal Design

**Orthogonality** means that a change to one component does not force a change to another. Two components are orthogonal when they are independent: you can modify, replace, or test either one without touching the other.

### Rules

- Separate concerns so that each module has one reason to change.
- A component should not need to know how another component is implemented — only what it does.
- Dependencies should flow in one direction. Circular dependencies are a sign of non-orthogonal design.
- Design so that swapping an implementation (e.g. switching from one database to another) requires no changes to any component that did not directly depend on it.

### Why It Matters for Testing

When components are orthogonal, you can test each one in isolation. A test for business logic should not break because the database schema changed. A test for an HTTP adapter should not break because domain rules changed. Orthogonal design is what makes this possible.

```
NON-ORTHOGONAL — business logic depends on Stripe directly:
  OrderService → StripeGateway
  Changing payment provider requires rewriting OrderService tests.

ORTHOGONAL — business logic depends on an interface:
  OrderService → PaymentGateway (interface)
                     ↑
               StripeAdapter  BraintreeAdapter
  Changing payment provider does not touch OrderService or its tests.
```

---

## Hexagonal Architecture (Ports and Adapters)

Hexagonal Architecture, defined by Alistair Cockburn, organises an application into three zones:

```
┌─────────────────────────────────────────────┐
│              DRIVING ADAPTERS               │  ← Tests, HTTP controllers, CLI, message consumers
│         (primary — drive the app)           │
├─────────────────────────────────────────────┤
│                                             │
│             APPLICATION CORE               │  ← Domain logic, use cases, business rules
│          (no I/O, no frameworks)            │
│                                             │
├─────────────────────────────────────────────┤
│              DRIVEN ADAPTERS                │  ← Database, email, external APIs, message queues
│       (secondary — driven by the app)       │
└─────────────────────────────────────────────┘
```

### Ports

A **port** is an interface defined by the application core. It describes what the application *needs* — not how it is provided.

- **Driving ports** (primary): interfaces through which external actors interact with the core (e.g. `OrderService`, `UserService`).
- **Driven ports** (secondary): interfaces the core calls outward (e.g. `PaymentGateway`, `UserRepository`, `EmailSender`).

Ports belong to the core. They are defined in terms of the domain, not in terms of any specific technology.

### Adapters

An **adapter** is a concrete implementation of a port. It translates between the application's domain language and an external system.

- A `StripeAdapter` implements `PaymentGateway`.
- A `PostgresUserRepository` implements `UserRepository`.
- An `HttpController` implements the driving port by calling `OrderService`.

Adapters belong outside the core. They depend on the core; the core does not depend on them.

### Rules

- The application core must not import or reference any adapter, framework, or I/O library.
- All I/O crosses the boundary through a port interface.
- Adapters are the only place where third-party libraries (ORMs, HTTP clients, SDKs) appear.
- Driven ports are what you inject into use cases and services — not concrete adapters.
- Wrap any third-party library you do not own in an adapter. Never let a third-party type leak into the core.

### Example

```
WRONG — core depends on a concrete adapter:
  class OrderService:
    def __init__(self):
      self.payment = StripeGateway()   ← adapter imported into core

CORRECT — core depends on a port:
  class OrderService:
    def __init__(self, payment: PaymentGateway):   ← port, not adapter
      self.payment = payment

In production:   OrderService(payment=StripeAdapter())
In tests:        OrderService(payment=FakePaymentGateway())
```

---

## How These Principles Drive the Mocking Rules

The "mock at system boundaries only" rule is a direct consequence of hexagonal architecture:

| Rule | Why |
|------|-----|
| Mock driven ports (external APIs, databases, etc.) | They are the outward boundary. Tests should verify the core behaves correctly given what the port returns. |
| Do not mock your own classes or internal collaborators | Those are inside the core. Mocking them means testing structure, not behaviour. |
| Mock interfaces (ports), not concrete implementations (adapters) | Tests should depend on the contract, not the wiring. |
| Wrap third-party libraries in an adapter; mock the adapter | You do not own the third-party interface — it can change. Your adapter is the stable contract. |
| Prefer dependency injection over internal construction | Ports must be injectable to be replaceable. |

Orthogonality enforces this further: if your tests are hard to write without mocking internal collaborators, it means two concerns are entangled and need to be separated — the design is not orthogonal.

```
SIGNAL: "I need to mock UserService to test OrderService"
CAUSE:  OrderService depends on UserService directly — they are not orthogonal
FIX:    Introduce a port that represents only what OrderService needs from user data,
        and depend on that interface instead
```

---

## Summary

- **Orthogonal design**: components change independently. Enables isolated testing.
- **Hexagonal architecture**: core logic is surrounded by ports (interfaces) and adapters (implementations). The core has no knowledge of external systems.
- **Consequence for mocking**: mock at ports (the boundary between core and adapters). Everything inside the core is tested directly; everything outside is replaced with a fake or stub.
- **Consequence for design**: if mocking feels painful, the boundary is in the wrong place — fix the design, not the test.

---

## Related Documents

- `global/solid.md` — the Dependency Inversion Principle (D) is the SOLID expression of hexagonal architecture; Interface Segregation (I) explains why ports should be narrow
- `global/gang-of-four.md` — the Adapter pattern is how adapters are implemented; Strategy explains why the core can swap adapters at runtime
- `global/dry.md` — keeping a single authoritative port definition prevents knowledge duplication across adapters

---

## patterns/adapter

# Adapter Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Adapter section). This document provides Python / LangChain-specific implementation rules and examples.

Wrap non-LangChain services behind LangChain's Runnable, Retriever, or Tool interfaces.

---

## Custom LLM Adapter

### Rules

- Extend `BaseChatModel` to wrap a custom or self-hosted LLM behind LangChain's interface.
- Implement `_generate` (sync) and optionally `_agenerate` (async).
- This allows custom LLMs to be used anywhere a `BaseChatModel` is expected.

### Example

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class CustomLLMAdapter(BaseChatModel):
    """Adapter for a custom REST-based LLM service."""

    api_url: str
    api_key: str
    model_name: str = "custom-model"

    @property
    def _llm_type(self) -> str:
        return "custom-llm"

    def _generate(self, messages: list[BaseMessage], stop=None, **kwargs) -> ChatResult:
        import httpx
        prompt = "\n".join(m.content for m in messages)
        response = httpx.post(
            f"{self.api_url}/generate",
            json={"prompt": prompt, "model": self.model_name},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        response.raise_for_status()
        text = response.json()["text"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

# Usage — substitutable for any BaseChatModel
chain = prompt | CustomLLMAdapter(api_url="http://localhost:8080", api_key="...") | StrOutputParser()
```

---

## Custom Retriever Adapter

### Rules

- Extend `BaseRetriever` to wrap any search system behind LangChain's retriever interface.
- Implement `_get_relevant_documents` (sync) and optionally `_aget_relevant_documents` (async).

### Example

```python
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

class ElasticsearchRetriever(BaseRetriever):
    """Adapter wrapping Elasticsearch as a LangChain retriever."""

    es_client: object  # elasticsearch.Elasticsearch
    index_name: str
    k: int = 4

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, **kwargs) -> list[Document]:
        results = self.es_client.search(
            index=self.index_name,
            body={"query": {"match": {"content": query}}, "size": self.k},
        )
        return [
            Document(
                page_content=hit["_source"]["content"],
                metadata={"id": hit["_id"], "score": hit["_score"]},
            )
            for hit in results["hits"]["hits"]
        ]

# Usage — works anywhere BaseRetriever is expected
retriever = ElasticsearchRetriever(es_client=es, index_name="documents")
rag_chain = create_rag_chain(llm, retriever)
```

---

## Service Adapter as Tool

### Rules

- Wrap external services (APIs, databases, SaaS platforms) as LangChain tools.
- The adapter translates between LangChain's tool interface and the external service's API.

```python
from langchain_core.tools import tool

class JiraAdapter:
    """Wraps the Jira REST API."""
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url
        self.api_token = api_token

    def search_issues(self, jql: str, max_results: int = 10) -> list[dict]:
        # Call Jira API
        ...

def create_jira_tool(jira: JiraAdapter) -> BaseTool:
    @tool
    def search_jira(query: str) -> str:
        """Search Jira issues using JQL. Use for finding bugs, tasks, and stories."""
        issues = jira.search_issues(f'text ~ "{query}"', max_results=5)
        return "\n".join(f"[{i['key']}] {i['summary']}" for i in issues)
    return search_jira
```

---

## global/coupling-cohesion

# Coupling and Cohesion

Low coupling and high cohesion are the two foundational measures of modular design quality. They were formalised by Larry Constantine in the 1960s and remain the most reliable indicators of whether a codebase will be easy or painful to change.

**Coupling** is the degree to which one module depends on another. Lower is better.
**Cohesion** is the degree to which the elements inside a module belong together. Higher is better.

A well-designed module does one thing well (high cohesion) and needs as little as possible from the outside world to do it (low coupling). These two properties reinforce each other: a module that does one thing tends to need fewer external dependencies; a module with few dependencies tends to have a clear, unified purpose.

---

## The Prime Directive: Minimise Dependencies

### Rules

- Every dependency is a liability. It must be imported, initialised, versioned, tested, and updated. Add a dependency only when the alternative is clearly worse.
- Depend on the narrowest interface that satisfies your need. If you need `send(message)`, depend on a `Sender` interface with one method — not on a full messaging SDK with fifty.
- Depend in the direction of stability. A frequently-changing module must not depend on another frequently-changing module. If both change, they will break each other.
- Prefer receiving dependencies over fetching them. A module that accepts collaborators as parameters can be used in any context. A module that imports them directly is bound to that specific implementation.
- Question every import. Before adding a dependency to a module, ask: can this responsibility be pushed to the caller, or handled at a boundary instead?

### Example

```
WRONG — module fetches its own dependencies, depends on three concrete things:
  import DatabaseClient from 'database-sdk'
  import EmailProvider from 'email-sdk'
  import Logger from 'logging-sdk'

  function registerUser(data):
    db = new DatabaseClient(env.DB_URL)
    email = new EmailProvider(env.EMAIL_KEY)
    log = new Logger()
    ...

RIGHT — module accepts what it needs, depends on narrow interfaces:
  function registerUser(data, repo: UserRepository, notifier: Notifier, log: Logger)
    # three narrow interfaces, each with 1-2 methods
    # caller decides what implementations to provide
```

---

## Coupling Types — Worst to Best

Understanding the type of coupling helps identify how to reduce it. Listed from most harmful to least:

| Level | Name | Description | How to fix |
|-------|------|-------------|------------|
| 1 | **Content coupling** | Module A directly modifies the internal data of module B | Enforce encapsulation; expose behaviour, not data |
| 2 | **Common coupling** | Two modules share mutable global state | Eliminate globals; pass state explicitly |
| 3 | **Control coupling** | A passes a flag to B that controls B's internal logic | Split B into two functions; let A call the right one |
| 4 | **Stamp coupling** | A passes a large data structure to B; B uses only part of it | Pass only what B needs; introduce a narrow type |
| 5 | **Data coupling** | A passes only the data B needs, as simple parameters | Acceptable — keep parameters minimal |
| 6 | **Message coupling** | A and B communicate only through well-defined message/event interfaces | Ideal for independent modules |

### Example — Control Coupling

```
WRONG — flag controls internal branching (control coupling):
  function sendNotification(user, message, isUrgent: boolean):
    if isUrgent:
      sms.send(user.phone, message)
    else:
      email.send(user.email, message)

RIGHT — two functions, caller decides:
  function sendSmsNotification(user, message)
  function sendEmailNotification(user, message)
```

### Example — Stamp Coupling

```
WRONG — entire Order passed to a function that only needs the total (stamp coupling):
  function calculateTax(order: Order):
    return order.total * TAX_RATE

RIGHT — pass only what is needed (data coupling):
  function calculateTax(orderTotal: Money):
    return orderTotal * TAX_RATE
```

---

## Cohesion Types — Best to Worst

High cohesion means the elements in a module genuinely belong together. Listed from most to least cohesive:

| Level | Name | Description |
|-------|------|-------------|
| 1 | **Functional** | Every element contributes to a single, well-defined task |
| 2 | **Sequential** | Output of one element feeds the next (pipeline) |
| 3 | **Communicational** | Elements operate on the same data |
| 4 | **Procedural** | Elements follow a sequence but are otherwise unrelated |
| 5 | **Temporal** | Elements are grouped because they happen at the same time (e.g. startup) |
| 6 | **Logical** | Elements are grouped by category but do unrelated things (e.g. a "utils" module) |
| 7 | **Coincidental** | Elements have no meaningful relationship |

Aim for functional or sequential cohesion. Logical and coincidental cohesion are signals to split the module.

```
LOW COHESION — "utils" module does unrelated things:
  utils.formatDate(date)
  utils.validateEmail(email)
  utils.hashPassword(pwd)
  utils.parseCsv(file)
  utils.sendSlack(msg)

HIGH COHESION — each module does one thing:
  DateFormatter.format(date)
  EmailValidator.validate(email)
  PasswordHasher.hash(pwd)
```

---

## Stable Dependencies Principle

Depend in the direction of stability. A module that changes frequently must not depend on another module that also changes frequently.

### Rules

- Stable modules (interfaces, domain models, utility functions) should be depended on freely — they rarely change.
- Unstable modules (HTTP handlers, UI components, adapters) should not be depended on by stable modules.
- If a stable module must use an unstable one, introduce an interface between them so the stable module depends on the interface (stable), not the implementation (unstable).
- Ports in hexagonal architecture are stable by design — they change only when the domain changes.

### Example

```
WRONG — stable domain logic depends on unstable infrastructure:
  OrderService (stable) → PostgresRepository (unstable — DB schema changes)

RIGHT — stable domain logic depends on a stable interface:
  OrderService (stable) → OrderRepository interface (stable)
                               ↑
                    PostgresRepository (unstable)
```

---

## Acyclic Dependencies Principle

The dependency graph must contain no cycles.

### Rules

- A cycle means two modules are so entangled that neither can be changed, tested, or released independently of the other.
- If module A depends on B and B depends on A, extract the shared concern into a third module C that both depend on.
- Run a dependency cycle check in CI for large codebases.
- Cycles in package/module imports are always a design problem — resolve the design rather than using workarounds like deferred imports.

### Example

```
CYCLE — neither can change without breaking the other:
  UserService → OrderService → UserService

FIX — extract the shared concept both need:
  UserService   →  AccountSummary (interface/type)
  OrderService  →  AccountSummary (interface/type)

  Neither UserService nor OrderService knows about the other.
```

---

## Dependency Budget

Treat dependencies as a budget, not a free resource.

### Rules

- For any module, count its direct imports/dependencies. If the count exceeds five to seven, the module likely has more than one responsibility.
- Each new package-level dependency (an npm package, a pip package, an imported library) adds a supply-chain risk, a versioning constraint, and a build-time cost. Justify it explicitly.
- Prefer using language built-ins and standard library before reaching for a third-party package.
- When evaluating a new package dependency, ask: is the value this provides worth the maintenance cost over the next two years?

---

## Related Documents

- `global/solid.md` — Interface Segregation Principle (I) enforces narrow interfaces; Dependency Inversion Principle (D) enforces depending on abstractions
- `global/hexagonal-architecture.md` — ports and adapters enforce the Stable Dependencies Principle structurally; orthogonal design is low coupling applied to component boundaries
- `global/dry.md` — knowledge duplication creates implicit coupling; the single authoritative representation reduces it
- `global/simplicity.md` — YAGNI prevents unnecessary dependencies from being added in the first place
- `global/object-interaction.md` — Law of Demeter is the method-level expression of low coupling

---

## patterns/decorator

# Decorator Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Decorator section). This document provides Python / LangChain-specific implementation rules and examples.

Extend chain and tool behaviour without modifying their source code.

---

## The @tool Decorator

### Rules

- Use `@tool` to convert plain functions into LangChain tools.
- Always provide a docstring — the LLM reads it to understand when and how to use the tool.
- Use type hints and Pydantic `Field` for argument descriptions.

### Example

```python
from langchain_core.tools import tool
from pydantic import Field

@tool
def search_knowledge_base(
    query: str = Field(description="The search query to find relevant documents"),
    max_results: int = Field(default=5, description="Maximum number of results to return"),
) -> str:
    """Search the internal knowledge base for documents matching the query.

    Use this tool when the user asks about company policies, procedures, or internal documentation.
    """
    results = vector_store.similarity_search(query, k=max_results)
    return "\n\n".join(doc.page_content for doc in results)
```

---

## Custom Retry Decorator

### Rules

- Wrap chain invocations with retry logic for transient LLM API failures.
- Use exponential backoff.
- Only retry on retryable errors (rate limits, timeouts), not on validation errors.

### Example

```python
import functools
import asyncio
import logging
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)

def retry_on_llm_error(max_attempts: int = 3, base_delay: float = 1.0):
    """Retry decorator for LLM chain invocations."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except OutputParserException:
                    raise  # Don't retry parse errors
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs",
                            fn.__name__, attempt, max_attempts, e, delay,
                        )
                        await asyncio.sleep(delay)
            raise last_error
        return wrapper
    return decorator

@retry_on_llm_error(max_attempts=3, base_delay=2.0)
async def summarize_document(text: str) -> str:
    return await summarize_chain.ainvoke({"text": text})
```

---

## Logging Decorator for Chains

```python
def with_logging(chain: Runnable, name: str) -> Runnable:
    """Wrap a chain with input/output logging."""
    async def log_and_run(input_data):
        logger.info("Chain '%s' started", name)
        result = await chain.ainvoke(input_data)
        logger.info("Chain '%s' completed", name)
        return result

    return RunnableLambda(log_and_run)

logged_chain = with_logging(summarize_chain, "summarize")
```

---

## Validation Decorator

```python
def validate_input(schema: type[BaseModel]):
    """Decorator to validate chain input against a Pydantic schema."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(input_data: dict, **kwargs):
            validated = schema(**input_data)
            return await fn(validated.model_dump(), **kwargs)
        return wrapper
    return decorator

class SummarizeInput(BaseModel):
    text: str = Field(min_length=10)
    max_sentences: int = Field(default=3, ge=1, le=20)

@validate_input(SummarizeInput)
async def summarize(input_data: dict) -> str:
    return await summarize_chain.ainvoke(input_data)
```

