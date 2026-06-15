# Standards for sync CLI command

The following standards apply to this work.

---

## ir/identity

Every `ir.py` value object is a `@dataclass(frozen=True)` whose identity is an **explicit
subset** of its fields. Mark every non-identity field `field(compare=False)`: it is
carried, but ignored by `==` and `hash()`.

```python
@dataclass(frozen=True)
class Node:
    id: str                                                # identity
    prose: str | None = field(compare=False, default=None) # carried, not identity
    loc: SourceLocation | None = field(compare=False, default=None)
```

Identity (the fields that compare) per type:

| type | identity |
| --- | --- |
| `Node` | `id` |
| `Edge` | `(src_id, dst_id, predicate)` |
| `Predicate` | `name` |
| `Route` | `(source_id, branches, else_target)` |
| `Attribute` | `(name, type_str, reducer)` |
| `DataModel` | `(name, style)` |
| `Meta` | `(owner_id, kind, data)` |
| `Diagnostic` | `(kind, subject, message)` |

`SourceLocation` is the one pure value object: all fields are identity. In `GraphModel`,
the dict containers key by a subset of identity — `nodes` by `id`, `predicates`/`models`
by `name`, `routes` by `source_id`.

### Why

lg2m reconciles three sources (topology, annotations, diagram). The same Node/Edge must
match its counterpart **across sources by identity** while still carrying provenance
(`loc`, `prose`, `docstring`) for the drift report. `compare=False` lets one object both
dedup/merge by identity and carry report data.

### Rules

- New field → add `field(compare=False, ...)` unless it is genuinely part of identity.
  Omitting it silently folds the field into identity and breaks cross-source matching.
- Put identity fields first (positional, no `compare=False`); non-identity fields follow.
- `Edge.predicate is None` means **unconditional**. Because `predicate` is part of
  identity: two predicates to the same target are two distinct edges (→ two labelled
  diagram edges), and an unconditional vs conditional edge between the same pair are
  different edges.

---

## ir/mutability

`GraphModel` is the ONE mutable container in `ir.py` (a plain `@dataclass`). Every value
object it holds is `frozen=True`.

```python
@dataclass            # mutable: the parse-then-assemble buffer
class GraphModel:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    ...
```

### Why

Parsers and the AST reader append nodes/edges/meta into `GraphModel` incrementally, across
passes and across the three sources, then it is read once to build the reconciled output.
Frozen contents stay safe to dedup and share while the buffer grows. `GraphModel` is never
used as a dict key, so it need not be hashable or frozen.

### Rules

- Mutate only `GraphModel`. Treat every Node/Edge/Predicate/Route as immutable once
  constructed; "changing" one means building a new instance.
- **Mutable field on a frozen instance** (e.g. `Node.meta: dict`): build the dict fully,
  THEN construct the Node. Never mutate `node.meta` afterward.
  - `frozen=True` blocks **rebinding** the attribute (`node.meta = {}`), not **mutating**
    the dict it points to (`node.meta[k] = v` still works, and is a bug here).
  - `meta` is `compare=False`, so a post-construction mutation silently changes contents
    with no equality/hash signal.

```python
meta = {"merges": "process_item (Send)"}   # build first
node = Node(id="map_items", meta=meta)      # then construct
# never: node.meta["merges"] = ...          # mutates a "frozen" object's dict
```

---

## global/coding-conventions

Project structure, imports, configuration, and naming conventions for LangChain applications.

### Project Structure

```
project/
├── pyproject.toml
├── src/
│   └── app/
│       ├── __init__.py
│       └── ...
└── tests/
    ├── conftest.py
    └── ...
```

### Rules

- One major component per file: one chain, one tool, one agent.
- Name files after the component.
- Group by component type, not by feature.
- Order: standard library → third-party → local application.

---

## global/tdd-workflow

Test-Driven Development is a design discipline, not a testing strategy. Tests written
before implementation drive smaller interfaces, tighter scope, and code that is testable
by construction.

### The Red-Green-Refactor Cycle

- **Red** — Write one failing test. Run it. Confirm it fails for the right reason.
- **Green** — Write the minimum code to make it pass.
- **Refactor** — Improve code while keeping all tests green.

### Rules

- Test behaviour through public interfaces only.
- Mock only at system boundaries.
- Test one logical concept per test case.
- Do not mark a task complete until all tests are green.
