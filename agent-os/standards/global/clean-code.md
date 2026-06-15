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
