# Builder Pattern — Python / LangChain

> For the language-agnostic pattern description, rationale, and when to use it, see `global/gang-of-four.md` (Builder section). This document provides Python / LangChain-specific implementation rules and examples.

Construct complex chains, prompts, and agent configurations step by step.

---

## Prompt Template Builder

### Rules

- Use a builder when prompts have many optional sections (few-shot examples, system context, format instructions).
- The builder assembles the final `ChatPromptTemplate` from parts.

### Example

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

class PromptBuilder:
    """Build chat prompts with optional sections."""

    def __init__(self):
        self._system_parts: list[str] = []
        self._messages: list[tuple] = []
        self._has_history = False

    def system(self, text: str) -> "PromptBuilder":
        self._system_parts.append(text)
        return self

    def with_history(self) -> "PromptBuilder":
        self._has_history = True
        return self

    def with_format_instructions(self, instructions: str) -> "PromptBuilder":
        self._system_parts.append(f"\nOutput format:\n{instructions}")
        return self

    def human(self, template: str) -> "PromptBuilder":
        self._messages.append(("human", template))
        return self

    def build(self) -> ChatPromptTemplate:
        messages = []
        if self._system_parts:
            messages.append(("system", "\n\n".join(self._system_parts)))
        if self._has_history:
            messages.append(MessagesPlaceholder("chat_history", optional=True))
        messages.extend(self._messages)
        return ChatPromptTemplate.from_messages(messages)

# Usage
prompt = (
    PromptBuilder()
    .system("You are a helpful research assistant.")
    .system("Always cite your sources.")
    .with_history()
    .with_format_instructions("Respond in JSON with 'answer' and 'sources' keys.")
    .human("{question}")
    .build()
)
```

---

## Chain Builder

### Rules

- Use a builder when chain construction has many optional steps (preprocessing, postprocessing, fallbacks, retries).

### Example

```python
from langchain_core.runnables import Runnable, RunnableLambda

class ChainBuilder:
    """Build chains with optional middleware steps."""

    def __init__(self, core_chain: Runnable):
        self._chain = core_chain
        self._preprocessors: list[Runnable] = []
        self._postprocessors: list[Runnable] = []
        self._fallback: Runnable | None = None

    def preprocess(self, fn) -> "ChainBuilder":
        self._preprocessors.append(RunnableLambda(fn))
        return self

    def postprocess(self, fn) -> "ChainBuilder":
        self._postprocessors.append(RunnableLambda(fn))
        return self

    def with_fallback(self, fallback_chain: Runnable) -> "ChainBuilder":
        self._fallback = fallback_chain
        return self

    def build(self) -> Runnable:
        chain = self._chain
        for pre in reversed(self._preprocessors):
            chain = pre | chain
        for post in self._postprocessors:
            chain = chain | post
        if self._fallback:
            chain = chain.with_fallbacks([self._fallback])
        return chain

# Usage
chain = (
    ChainBuilder(prompt | llm | StrOutputParser())
    .preprocess(lambda x: {**x, "text": x["text"].strip()})
    .postprocess(lambda x: x.strip())
    .with_fallback(fallback_prompt | fallback_llm | StrOutputParser())
    .build()
)
```

---

## Agent Builder

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent

class AgentBuilder:
    def __init__(self, llm: BaseChatModel):
        self._llm = llm
        self._tools: list[BaseTool] = []
        self._prompt = DEFAULT_AGENT_PROMPT
        self._max_iterations = 10
        self._verbose = False

    def tools(self, *tools: BaseTool) -> "AgentBuilder":
        self._tools.extend(tools)
        return self

    def prompt(self, prompt: ChatPromptTemplate) -> "AgentBuilder":
        self._prompt = prompt
        return self

    def max_iterations(self, n: int) -> "AgentBuilder":
        self._max_iterations = n
        return self

    def verbose(self) -> "AgentBuilder":
        self._verbose = True
        return self

    def build(self) -> AgentExecutor:
        agent = create_tool_calling_agent(self._llm, self._tools, self._prompt)
        return AgentExecutor(
            agent=agent,
            tools=self._tools,
            max_iterations=self._max_iterations,
            verbose=self._verbose,
            handle_parsing_errors=True,
        )

# Usage
agent = (
    AgentBuilder(llm)
    .tools(search_tool, calculator_tool, jira_tool)
    .max_iterations(15)
    .build()
)
```
