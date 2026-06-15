# Composition Patterns — Python / LangChain (LCEL)

LangChain Expression Language (LCEL) is built on composition. Build complex chains by combining simple, reusable runnables.

---

## Pipe Operator (|)

### Rules

- Use `|` to compose runnables sequentially: `prompt | llm | parser`.
- Each step's output becomes the next step's input.
- Read chains top-to-bottom, left-to-right.

### Example

```python
chain = (
    ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "{question}"),
    ])
    | ChatOpenAI(model="gpt-4o")
    | StrOutputParser()
)

result = await chain.ainvoke({"question": "What is LCEL?"})
```

---

## RunnableSequence

The pipe operator creates a `RunnableSequence` under the hood.

```python
from langchain_core.runnables import RunnableSequence

# Explicit (equivalent to pipe)
chain = RunnableSequence(first=prompt, middle=[llm], last=parser)

# Pipe syntax is preferred
chain = prompt | llm | parser
```

---

## RunnableParallel

### Rules

- Use `RunnableParallel` (or a dict) to run multiple runnables concurrently.
- Each key in the dict becomes a key in the output dict.
- Use for assembling context from multiple sources.

### Example

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

# Dict syntax (shorthand for RunnableParallel)
setup = {
    "context": retriever | format_docs,
    "question": RunnablePassthrough(),
}

rag_chain = setup | rag_prompt | llm | StrOutputParser()

# Explicit RunnableParallel
parallel = RunnableParallel(
    summary=summarize_chain,
    classification=classify_chain,
    sentiment=sentiment_chain,
)

results = await parallel.ainvoke({"text": document})
# results = {"summary": "...", "classification": {...}, "sentiment": "positive"}
```

---

## RunnablePassthrough

### Rules

- Use `RunnablePassthrough()` to pass input through unchanged.
- Use `RunnablePassthrough.assign()` to add computed fields to the input.

### Example

```python
from langchain_core.runnables import RunnablePassthrough

# Pass input through while adding computed context
chain = (
    RunnablePassthrough.assign(
        context=lambda x: retriever.invoke(x["question"]),
        word_count=lambda x: len(x["question"].split()),
    )
    | prompt
    | llm
    | StrOutputParser()
)
```

---

## RunnableBranch

### Rules

- Use `RunnableBranch` for conditional routing based on input.
- Define conditions as `(predicate, runnable)` tuples.
- Always provide a default branch (last argument).

### Example

```python
from langchain_core.runnables import RunnableBranch

routing_chain = RunnableBranch(
    (lambda x: x["type"] == "summary", summarize_chain),
    (lambda x: x["type"] == "classify", classify_chain),
    (lambda x: x["type"] == "translate", translate_chain),
    default_chain,  # Fallback
)

result = await routing_chain.ainvoke({"type": "summary", "text": "..."})
```

---

## RunnableLambda

### Rules

- Use `RunnableLambda` to wrap plain functions as runnables.
- Useful for data transformation steps between chain components.
- For async functions, the lambda is automatically awaited.

### Example

```python
from langchain_core.runnables import RunnableLambda

format_docs = RunnableLambda(
    lambda docs: "\n\n".join(doc.page_content for doc in docs)
)

parse_json = RunnableLambda(lambda text: json.loads(text))

chain = retriever | format_docs | prompt | llm | StrOutputParser() | parse_json
```

---

## Composition Over Inheritance

### Rules

- Build chains by composing runnables, not by subclassing.
- Avoid creating custom Runnable subclasses unless absolutely necessary.
- Use `RunnableLambda` for custom logic instead of subclassing `Runnable`.
- Compose small chains into larger ones rather than building monolithic chains.

```python
# Small, reusable building blocks
preprocess = RunnableLambda(lambda x: {**x, "text": x["text"].strip().lower()})
postprocess = RunnableLambda(lambda x: x.strip())

# Compose into chains
simple_chain = preprocess | prompt | llm | StrOutputParser() | postprocess
rag_chain = preprocess | {"context": retriever | format_docs, "text": RunnablePassthrough()} | prompt | llm | StrOutputParser() | postprocess
```
