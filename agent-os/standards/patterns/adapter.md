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
