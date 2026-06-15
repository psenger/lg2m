"""Per-import registry that the lg2m annotations and router populate.

A mutable assembly buffer (compare ir.GraphModel): the decorators write into it
as the user's module imports; lg2m later reads it to build the IR. It is a
module-level singleton so the decorators need not thread anything through, and
``reset()`` restores a clean buffer for per-graph isolation and test independence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NodeEntry:
    id: str
    target: Callable[..., Any]
    module: str | None
    lineno: int | None
    docstring: str | None = field(compare=False, default=None)  # reader-recovered prose


@dataclass(frozen=True)
class PredicateEntry:
    name: str
    target: Callable[..., Any]
    module: str | None
    lineno: int | None
    docstring: str | None = field(compare=False, default=None)  # reader-recovered prose


@dataclass(frozen=True)
class ModelEntry:
    name: str  # class __name__
    target: type
    is_graph_state: bool  # True for @state_model, False for @data_model
    module: str | None
    lineno: int | None


@dataclass(frozen=True)
class RouterEntry:
    source: str
    branches: tuple[tuple[str, str], ...]
    else_target: str
    path_fn: Callable[[Any], str]
    module: str | None
    lineno: int | None


@dataclass
class Registry:
    nodes: dict[str, NodeEntry] = field(default_factory=dict)
    predicates: dict[str, PredicateEntry] = field(default_factory=dict)
    models: dict[str, ModelEntry] = field(default_factory=dict)
    routers: dict[str, RouterEntry] = field(default_factory=dict)

    def reset(self) -> None:
        self.nodes.clear()
        self.predicates.clear()
        self.models.clear()
        self.routers.clear()


_REGISTRY = Registry()


def get_registry() -> Registry:
    return _REGISTRY


def reset() -> None:
    """Clear the shared registry. Call between graphs and in test teardown."""
    _REGISTRY.reset()
