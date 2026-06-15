# Factory Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Factory Method and Abstract Factory sections). This document provides Python / LangChain-specific implementation rules and examples.

Create LLMs, chains, tools, and agents through factory functions that hide instantiation details.

---

## LLM Factory

### Rules

- Centralise LLM creation in a factory that reads from configuration.
- Accept `BaseChatModel` in chain factories — never hardcode a provider.
- Use the factory to switch providers without touching chain code.

### Example

```python
from langchain_core.language_models import BaseChatModel
from app.config.settings import Settings

def create_llm(settings: Settings) -> BaseChatModel:
    """Create an LLM instance based on configuration."""
    match settings.llm_provider:
        case "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        case _:
            raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

---

## Chain Factory

### Rules

- Chain factories accept dependencies (LLM, retriever) as parameters.
- Return typed `Runnable[InputType, OutputType]`.
- Name factories `create_<purpose>_chain`.

### Example

```python
from langchain_core.runnables import Runnable

def create_summarize_chain(llm: BaseChatModel) -> Runnable[dict, str]:
    """Create a summarization chain.

    Input: {"text": str, "max_sentences": int}
    Output: Summary string.
    """
    return SUMMARIZE_PROMPT | llm | StrOutputParser()

def create_rag_chain(
    llm: BaseChatModel,
    retriever: BaseRetriever,
) -> Runnable[str, str]:
    """Create a RAG chain.

    Input: Question string.
    Output: Answer string with citations.
    """
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
```

---

## Tool Factory

### Rules

- Use `@tool` decorator for simple tools.
- Use factory functions for configurable tools that need injected dependencies.

### Example

```python
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """Search the web for information about the query."""
    results = search_client.search(query, max_results=5)
    return "\n".join(r.snippet for r in results)

# Factory for configurable tools
def create_database_tool(db_connection: DatabaseConnection) -> BaseTool:
    @tool
    def query_database(sql: str) -> str:
        """Execute a read-only SQL query against the database."""
        if not sql.strip().upper().startswith("SELECT"):
            return "Error: Only SELECT queries are allowed."
        results = db_connection.execute(sql)
        return json.dumps(results, default=str)

    return query_database
```

---

## Agent Factory

```python
from langchain.agents import create_tool_calling_agent, AgentExecutor

def create_research_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
) -> AgentExecutor:
    """Create a research agent with the given tools."""
    agent = create_tool_calling_agent(llm, tools, RESEARCH_AGENT_PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=10,
        handle_parsing_errors=True,
    )
```
