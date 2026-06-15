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
