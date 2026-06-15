# IR Mutability Boundary

`GraphModel` is the ONE mutable container in `ir.py` (a plain `@dataclass`). Every value
object it holds is `frozen=True`.

```python
@dataclass            # mutable: the parse-then-assemble buffer
class GraphModel:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    ...
```

## Why

Parsers and the AST reader append nodes/edges/meta into `GraphModel` incrementally, across
passes and across the three sources, then it is read once to build the reconciled output.
Frozen contents stay safe to dedup and share while the buffer grows. `GraphModel` is never
used as a dict key, so it need not be hashable or frozen.

## Rules

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
