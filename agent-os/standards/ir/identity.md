# IR Value-Object Identity

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

## Why

lg2m reconciles three sources (topology, annotations, diagram). The same Node/Edge must
match its counterpart **across sources by identity** while still carrying provenance
(`loc`, `prose`, `docstring`) for the drift report. `compare=False` lets one object both
dedup/merge by identity and carry report data.

## Rules

- New field → add `field(compare=False, ...)` unless it is genuinely part of identity.
  Omitting it silently folds the field into identity and breaks cross-source matching.
- Put identity fields first (positional, no `compare=False`); non-identity fields follow.
- `Edge.predicate is None` means **unconditional**. Because `predicate` is part of
  identity: two predicates to the same target are two distinct edges (→ two labelled
  diagram edges), and an unconditional vs conditional edge between the same pair are
  different edges.
