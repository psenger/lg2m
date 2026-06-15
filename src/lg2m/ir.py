"""Intermediate representation for lg2m: framework-free value objects.

Identity rules (docs/design.md Section 6) are enforced structurally:
  Node      identity = id
  Edge      identity = (src_id, dst_id, predicate)   # predicate None => unconditional
  Predicate identity = name
  Route     keyed by source_id in GraphModel.routes
  DataModel keyed by name in GraphModel.models

Each value object is a frozen dataclass. Equality and hashing cover only the
identity fields; every other field is marked ``field(compare=False)`` so it is
carried but does not participate in identity. ``GraphModel`` is the single
mutable, non-identity container (the parse-then-assemble buffer); it is never
used as a dict key, so it is a plain dataclass.

Discipline for ``Node.meta`` (a mutable dict on a frozen instance): build the
dict first, then construct the ``Node``. ``frozen=True`` blocks rebinding the
attribute, not mutating the dict it points to, so never mutate ``node.meta``
after construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# The reserved Mermaid label for a router's required default branch. Shared by
# parsing/mermaid.py and annotations/* so the diagram label, the path_map default
# key, and the IR Route default are one literal and cannot disagree.
ELSE_LABEL = "[else]"


class NodeKind(str, Enum):
    NODE = "node"
    START = "start"
    END = "end"


class MetaKind(str, Enum):
    TABLE = "table"  # visible key/value table under an entity heading
    FENCE = "fence"  # hidden  <!-- lg2m: k=v; k=v -->
    NOTE = "note"  # free-text  > Note: ...


class DiagnosticKind(str, Enum):
    COMMAND_WITHOUT_DESTINATIONS = "command_without_destinations"
    SEND_WITHOUT_DESTINATIONS = "send_without_destinations"
    NON_ENUMERABLE_TARGETS = "non_enumerable_targets"
    IMPORT_FAILURE = "import_failure"
    MISSING_ELSE = "missing_else"
    ROUTER_NOT_WIRED = "router_not_wired"
    PARSE_ERROR = "parse_error"  # foundation layer: malformed markdown/mermaid/toml


@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    col: int | None = None


@dataclass(frozen=True)
class Node:
    id: str
    kind: NodeKind = field(compare=False, default=NodeKind.NODE)
    is_subgraph: bool = field(compare=False, default=False)
    anno_id: str | None = field(compare=False, default=None)
    prose: str | None = field(compare=False, default=None)
    docstring: str | None = field(compare=False, default=None)
    meta: dict[str, Any] = field(compare=False, default_factory=dict)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Edge:
    src_id: str
    dst_id: str
    predicate: str | None = None  # part of identity; None => unconditional
    conditional: bool = field(compare=False, default=False)
    is_else: bool = field(compare=False, default=False)
    parallel: bool = field(compare=False, default=False)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Predicate:
    name: str
    prose: str | None = field(compare=False, default=None)
    docstring: str | None = field(compare=False, default=None)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Route:
    source_id: str
    branches: tuple[tuple[str, str], ...]  # ordered (predicate_name, target_id)
    else_target: str
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Attribute:
    name: str
    type_str: str
    reducer: str | None = None
    description: str | None = field(compare=False, default=None)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class DataModel:
    name: str
    style: str  # "TypedDict" | "BaseModel" | ...
    is_graph_state: bool = field(compare=False, default=False)
    anno: str | None = field(compare=False, default=None)
    attributes: tuple[Attribute, ...] = field(compare=False, default=())
    prose: str | None = field(compare=False, default=None)
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Meta:
    owner_id: str
    kind: MetaKind
    data: Any  # dict for TABLE/FENCE, str for NOTE
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass(frozen=True)
class Diagnostic:
    kind: DiagnosticKind
    subject: str
    message: str
    loc: SourceLocation | None = field(compare=False, default=None)


@dataclass
class GraphModel:
    graph_id: str
    origin: str  # "markdown" | "code" | "merged"
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    predicates: dict[str, Predicate] = field(default_factory=dict)
    routes: dict[str, Route] = field(default_factory=dict)
    models: dict[str, DataModel] = field(default_factory=dict)
    meta: list[Meta] = field(default_factory=list)
    state_model_name: str | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
