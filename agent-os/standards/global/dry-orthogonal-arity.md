# DRY, Orthogonal Design, and Function Arity — Python / LangChain

> For the language-agnostic DRY principles and theory, see `global/dry.md` from the default profile. For orthogonal design and hexagonal architecture, see `global/hexagonal-architecture.md`. This document extends those principles with Python / LangChain-specific rules, examples, and LCEL composition guidance.

Principles for building reusable, decoupled, and composable LangChain applications.

---

## DRY — Don't Repeat Yourself

### Rules

- Define each prompt template once in a `prompts/` module — never duplicate prompts across chains.
- Create reusable chain factories instead of copy-pasting chain definitions.
- Centralise LLM configuration in a settings/factory module.
- Share Pydantic models across chains that produce the same output structure.
- Reuse output parsers — don't create new parser instances for the same schema.

### Example

```python
# BAD — prompt duplicated across two modules
# chains/summarize.py
prompt1 = ChatPromptTemplate.from_messages([("system", "Summarize..."), ("human", "{text}")])
# chains/report.py
prompt2 = ChatPromptTemplate.from_messages([("system", "Summarize..."), ("human", "{text}")])

# GOOD — single source of truth
# prompts/summarization.py
SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Summarize the text in {max_sentences} sentences."),
    ("human", "{text}"),
])

# Both chains reference the same prompt
summarize_chain = SUMMARIZE_PROMPT | llm | StrOutputParser()
report_chain = SUMMARIZE_PROMPT | report_llm | StrOutputParser()
```

---

## Orthogonal Design

### Rules

- Keep concerns separate: prompts, LLM config, chain logic, output parsing, and persistence are independent axes.
- Chains should be pure transforms — no database writes or API calls inside chain steps.
- Use callbacks for cross-cutting concerns (logging, tracing, metrics) — don't embed them in chains.
- Retrievers are orthogonal to chains — swap vector stores without changing chain logic.

### Example

```python
# BAD — database write inside chain
def save_result(result):
    db.save(result)  # Side effect coupled to chain
    return result

chain = prompt | llm | parser | RunnableLambda(save_result)

# GOOD — chain is a pure transform; persistence is separate
chain = prompt | llm | parser  # Pure

# Orchestration layer handles side effects
async def process_and_save(input_data: dict) -> Result:
    result = await chain.ainvoke(input_data)
    await db.save(result)  # Separate concern
    return result
```

---

## Function Arity

### Rules

- Chain factories should accept 1-3 parameters (LLM, retriever, config).
- Use a config dataclass when a factory needs many options.
- LCEL chains are naturally monadic — one input dict, one output.
- Tool functions should have clear, minimal parameters with Pydantic `Field` descriptions.

### Example

```python
# BAD — too many parameters
def create_rag_chain(llm, retriever, prompt, parser, k, score_threshold, reranker):
    ...

# GOOD — config object
@dataclass
class RAGConfig:
    k: int = 4
    score_threshold: float = 0.7
    reranker: BaseDocumentCompressor | None = None

def create_rag_chain(
    llm: BaseChatModel,
    retriever: BaseRetriever,
    config: RAGConfig | None = None,
) -> Runnable[str, str]:
    config = config or RAGConfig()
    ...
```

---

## Composable Runnables

LCEL is designed for composition — build complex chains from small, reusable pieces.

```python
# Reusable building blocks
format_docs = RunnableLambda(lambda docs: "\n\n".join(d.page_content for d in docs))
extract_question = RunnableLambda(lambda x: x["question"])

# Compose into different chains
rag_chain = (
    {"context": retriever | format_docs, "question": extract_question}
    | rag_prompt
    | llm
    | StrOutputParser()
)

# Reuse format_docs in a different chain
search_chain = (
    {"results": search_retriever | format_docs, "query": RunnablePassthrough()}
    | search_prompt
    | llm
    | StrOutputParser()
)
```
