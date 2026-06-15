# IR Kind Enums

Kind enums in `ir.py` subclass `(str, Enum)`:

```python
class NodeKind(str, Enum):
    NODE = "node"
    START = "start"
    END = "end"
```

`NodeKind`, `MetaKind`, `DiagnosticKind` all follow this.

## Why

A member both IS an enum and compares/serialises as its plain string:

```python
NodeKind.NODE == "node"             # True
json.dumps({"kind": NodeKind.NODE}) # '{"kind": "node"}'
```

So parse and round-trip code matches raw `"node"` / `"table"` literals and emits strings
directly, with no `.value` plumbing.

## Rules

- New kind enum → `class XKind(str, Enum)`, each member a lowercase string literal.
- Do **not** use `enum.StrEnum`: it is Python 3.11+, and the project targets 3.10
  (`requires-python >= 3.10`). `(str, Enum)` is the 3.10-compatible equivalent.
- Compare members to string literals directly (`kind == "node"`); no `.value`.
