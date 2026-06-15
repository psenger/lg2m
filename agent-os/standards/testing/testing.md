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
