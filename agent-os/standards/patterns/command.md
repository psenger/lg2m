# Command Pattern — Python / LangChain

> For the language-agnostic pattern description and rationale, see `global/gang-of-four.md` (Command section). This document provides Python / LangChain-specific rules and examples.

Encapsulate agent tool invocations and pipeline operations as Pydantic command objects. Handlers execute the commands. This makes LangChain tool calls structured, validatable, and serialisable.

---

## Rules

- Represent each agent tool invocation as a Pydantic model (`BaseModel`) — the model is the command.
- Handlers are functions or callables wrapped with `RunnableLambda`.
- Commands are validated by Pydantic at construction time; invalid inputs raise before any LLM call.
- Async execution is the default — always implement `ainvoke` where latency matters.
- Keep tool input schemas minimal; the agent should not need to supply implementation details.
- Separate command definition (the Pydantic schema) from command execution (the handler function).

---

## Example — Agent Tool Invocations as Commands

Each LangChain tool call is a command: the structured input is the command object, the tool's implementation is the handler.

```python
# app/tools/search_tool.py
from pydantic import BaseModel, Field
from langchain_core.tools import tool

class SearchCommand(BaseModel):
    """Command for searching the knowledge base."""
    query: str = Field(description="The search query text.")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of results to return.")
    filter_category: str | None = Field(default=None, description="Optional category filter.")

@tool(args_schema=SearchCommand)
async def search_knowledge_base(query: str, top_k: int = 4, filter_category: str | None = None) -> str:
    """Search the knowledge base for relevant information."""
    from app.services.retrieval_service import retrieval_service

    docs = await retrieval_service.search(
        query=query,
        k=top_k,
        filter={"category": filter_category} if filter_category else None,
    )
    return "\n\n".join(f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs))
```

```python
# app/tools/crm_tool.py
from pydantic import BaseModel, Field, EmailStr
from langchain_core.tools import tool

class UpdateCustomerCommand(BaseModel):
    """Command for updating a customer record in the CRM."""
    customer_id: str = Field(description="The unique customer identifier.")
    email: EmailStr | None = Field(default=None, description="New email address.")
    tier: str | None = Field(default=None, description="New subscription tier.")
    notes: str | None = Field(default=None, description="Notes to append to the customer record.")

@tool(args_schema=UpdateCustomerCommand)
async def update_customer(
    customer_id: str,
    email: str | None = None,
    tier: str | None = None,
    notes: str | None = None,
) -> str:
    """Update a customer record in the CRM."""
    from app.services.crm_service import crm_service

    updates = {k: v for k, v in {"email": email, "tier": tier, "notes": notes}.items() if v is not None}
    if not updates:
        return "No updates provided."

    await crm_service.update_customer(customer_id, **updates)
    return f"Customer {customer_id} updated: {', '.join(updates.keys())}"
```

---

## Example — Structured Tool Inputs as Command Objects

```python
# app/tools/report_tool.py
from pydantic import BaseModel, Field
from typing import Literal
from langchain_core.tools import StructuredTool

class GenerateReportCommand(BaseModel):
    """Command for generating a business report."""
    report_type: Literal["sales", "inventory", "customer_churn"] = Field(
        description="The type of report to generate."
    )
    start_date: str = Field(description="Start date in YYYY-MM-DD format.")
    end_date: str = Field(description="End date in YYYY-MM-DD format.")
    format: Literal["summary", "detailed"] = Field(
        default="summary",
        description="Level of detail in the report."
    )

async def handle_generate_report(
    report_type: str,
    start_date: str,
    end_date: str,
    format: str = "summary",
) -> str:
    """Handler: executes the GenerateReportCommand."""
    from app.services.reporting_service import reporting_service

    report = await reporting_service.generate(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        detailed=(format == "detailed"),
    )
    return report.to_markdown()


generate_report_tool = StructuredTool.from_function(
    coroutine=handle_generate_report,
    name="generate_report",
    description="Generate a business intelligence report for a given date range.",
    args_schema=GenerateReportCommand,
)
```

---

## Example — RunnableLambda as a Command Handler

Use `RunnableLambda` to wrap a command handler function in the LCEL chain model.

```python
# app/chains/document_processing_chain.py
from dataclasses import dataclass
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document

@dataclass(frozen=True)
class ChunkDocumentCommand:
    content: str
    source: str
    chunk_size: int = 512
    chunk_overlap: int = 64

@dataclass(frozen=True)
class EmbedChunksCommand:
    chunks: tuple[str, ...]
    model: str = "text-embedding-3-small"


def handle_chunk_document(command: ChunkDocumentCommand) -> list[str]:
    """Split document content into overlapping chunks."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=command.chunk_size,
        chunk_overlap=command.chunk_overlap,
    )
    return splitter.split_text(command.content)


async def handle_embed_chunks(command: EmbedChunksCommand) -> list[list[float]]:
    """Embed a list of text chunks and return vectors."""
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model=command.model)
    return await embeddings.aembed_documents(list(command.chunks))


# Build a pipeline from command handlers
chunk_handler = RunnableLambda(handle_chunk_document)
embed_handler = RunnableLambda(handle_embed_chunks)

# Usage
async def index_document(content: str, source: str) -> list[list[float]]:
    chunks = await chunk_handler.ainvoke(
        ChunkDocumentCommand(content=content, source=source)
    )
    return await embed_handler.ainvoke(
        EmbedChunksCommand(chunks=tuple(chunks))
    )
```

---

## Async Command Execution

All command handlers that touch external services should expose an async interface.

```python
# app/handlers/pipeline_command_handler.py
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel

class SummariseDocumentCommand(BaseModel):
    content: str
    max_words: int = 150
    language: str = "en"

class SummariseDocumentHandler:
    def __init__(self, llm: BaseChatModel) -> None:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarise the following text in {max_words} words or fewer. Respond in {language}."),
            ("human", "{content}"),
        ])
        self._chain = prompt | llm | StrOutputParser()

    async def execute(self, command: SummariseDocumentCommand) -> str:
        return await self._chain.ainvoke({
            "content": command.content,
            "max_words": command.max_words,
            "language": command.language,
        })

# Usage
handler = SummariseDocumentHandler(llm=ChatOpenAI(model="gpt-4o-mini"))
command = SummariseDocumentCommand(content=long_text, max_words=100)
summary = await handler.execute(command)
```
