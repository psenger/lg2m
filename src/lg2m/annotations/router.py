"""lg2m.router: the Model-A routing spine (a factory generating the path_fn).

router(source, branches) is a FACTORY that generates the LangGraph path_fn from
an ordered [(predicate_name, target), ..., (ELSE, target)] mapping and OWNS the
path_map. The generated selector resolves each predicate name to its @predicate
function lazily from the registry (the router module need not import predicates),
evaluates them in order on the post-node state, and returns the NAME of the first
truthy predicate, or the reserved "[else]" key. Because the diagram labels, the
runtime selector, and the path_map all come from this one mapping, they cannot
drift (docs/design.md Section 3).

Deferred hook (LangChain layer, NOT this layer): the same mapping will also emit a
RunnableBranch via a future .as_runnable_branch(); that method is intentionally
absent here so this module stays framework-free.
"""

from __future__ import annotations

from typing import Any

from lg2m.annotations.registry import RouterEntry, get_registry
from lg2m.ir import ELSE_LABEL


class _Else:
    """The required no-match default sentinel for a router mapping.

    A single module-level instance, exported as lg2m.ELSE. In the diagram and the
    path_map it serialises to the reserved "[else]" key.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "lg2m.ELSE"


ELSE = _Else()


class Router:
    """Generated selector for one conditional fan-out, plus its introspection view.

    Callable: ``Router(state) -> str`` (a predicate name, or ``"[else]"``).
    Attributes consumed by lg2m to build an IR Route and the add_conditional_edges
    path_map: ``source``, ``branches``, ``else_target``, ``path_map``.
    """

    def __init__(
        self, source: str, branches: tuple[tuple[str, str], ...], else_target: str
    ) -> None:
        self.source = source
        self.branches = branches  # ordered (predicate_name, target)
        self.else_target = else_target
        # path_map keyed by predicate name; ELSE_LABEL reserved. Two predicates to
        # the SAME target are two distinct keys -> two labelled edges (docs/design.md Section 6).
        self.path_map: dict[str, str] = {name: target for name, target in branches}
        self.path_map[ELSE_LABEL] = else_target

    def __call__(self, state: Any) -> str:
        reg = get_registry()
        for name, _target in self.branches:
            entry = reg.predicates.get(name)
            if entry is None:
                raise LookupError(
                    f"router({self.source!r}) references predicate {name!r}, "
                    f"which is not a registered @predicate"
                )
            if entry.target(state):
                return name
        return ELSE_LABEL


def router(source: str, branches: list[tuple[Any, str]]) -> Router:
    """Build and register the generated selector for a conditional fan-out."""
    _require_nonempty(source, "router source")
    parsed, else_target = _validate_branches(branches)
    selector = Router(source, parsed, else_target)
    get_registry().routers[source] = RouterEntry(
        source, parsed, else_target, selector, None, None
    )
    return selector


def _validate_branches(
    branches: list[tuple[Any, str]],
) -> tuple[tuple[tuple[str, str], ...], str]:
    if not isinstance(branches, (list, tuple)) or not branches:
        raise ValueError("router branches must be a non-empty list of (predicate, target)")

    pairs: list[tuple[str, str]] = []
    else_target: str | None = None

    for pair in branches:
        if not (isinstance(pair, tuple) and len(pair) == 2):
            raise ValueError(f"each branch must be a (predicate, target) pair, got {pair!r}")
        key, target = pair
        _require_nonempty(target, "branch target")

        if key is ELSE:
            if else_target is not None:
                raise ValueError("router has more than one ELSE default; exactly one is required")
            else_target = target
            continue

        _require_nonempty(key, "predicate name")
        if key == ELSE_LABEL:
            raise ValueError(f"predicate name cannot be the reserved label {ELSE_LABEL!r}")
        pairs.append((key, target))

    if else_target is None:
        raise ValueError("router is missing the required ELSE default")
    if not pairs:
        raise ValueError("router needs at least one predicate branch besides ELSE")

    return tuple(pairs), else_target


def _require_nonempty(value: Any, what: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty string, got {value!r}")
