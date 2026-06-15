"""lg2m authoring decorators: metadata only, target returned unchanged.

Parametrized:  @node("id")   @predicate("name")
Bare:          @state_model   @data_model

Every decorator records an entry into the per-import registry and returns the
decorated object untouched, so it never alters LangGraph/LangChain run-time
behaviour (docs/design.md Section 4). Line numbers recorded here are best-effort; the AST
reader (reader.py) is the authority on file:line and merges by id/name.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from lg2m.annotations.registry import ModelEntry, NodeEntry, PredicateEntry, get_registry
from lg2m.ir import ELSE_LABEL

F = TypeVar("F", bound=Callable[..., Any])
C = TypeVar("C", bound=type)


def node(node_id: str) -> Callable[[F], F]:
    """Link a node function to its diagram state and `### id` prose.

    Records (id -> function) and returns the function unchanged. The id is
    explicit by contract (PLAN: never inferred from __name__).
    """
    _require_nonempty(node_id, "node id")
    reg = get_registry()

    def decorate(fn: F) -> F:
        reg.nodes[node_id] = NodeEntry(
            node_id, fn, getattr(fn, "__module__", None), _func_lineno(fn)
        )
        return fn

    return decorate


def predicate(name: str) -> Callable[[F], F]:
    """Mark a function as a whole leaf condition for a Model-A fan-out.

    Records (name -> function). The router resolves predicate names to these
    functions lazily at call time.
    """
    _require_nonempty(name, "predicate name")
    if name == ELSE_LABEL:
        raise ValueError(f"predicate name cannot be the reserved label {ELSE_LABEL!r}")
    reg = get_registry()

    def decorate(fn: F) -> F:
        reg.predicates[name] = PredicateEntry(
            name, fn, getattr(fn, "__module__", None), _func_lineno(fn)
        )
        return fn

    return decorate


def state_model(cls: C) -> C:
    """Bare decorator: mark the graph-state model. Returns the class unchanged."""
    return _record_model(cls, is_graph_state=True)


def data_model(cls: C) -> C:
    """Bare decorator: mark a payload data model. Returns the class unchanged."""
    return _record_model(cls, is_graph_state=False)


def _record_model(cls: C, *, is_graph_state: bool) -> C:
    get_registry().models[cls.__name__] = ModelEntry(
        cls.__name__, cls, is_graph_state, getattr(cls, "__module__", None), _class_lineno(cls)
    )
    return cls


def _func_lineno(target: Callable[..., Any]) -> int | None:
    code = getattr(target, "__code__", None)
    return getattr(code, "co_firstlineno", None) if code is not None else None


def _class_lineno(cls: type) -> int | None:
    try:
        return inspect.getsourcelines(cls)[1]
    except (OSError, TypeError):
        return None


def _require_nonempty(value: Any, what: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty string, got {value!r}")
