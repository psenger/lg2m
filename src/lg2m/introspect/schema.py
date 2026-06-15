"""Framework-free introspection of a state-schema / payload class into a DataModel.

Reused by the langgraph adapter for both the graph-state schema (a ``TypedDict`` whose
``Annotated[T, reducer]`` channels carry reducers) and each ``@data_model`` payload class
(a pydantic ``BaseModel`` or a plain annotated class). It imports no framework: pydantic
models are read by duck-typing ``model_fields``; TypedDicts via ``typing.get_type_hints``.

Reducer matching is name-level (docs/design.md Section 12): a reducer in the ``operator`` module is
rendered module-qualified (``operator.add``), everything else by ``__name__``
(``add_messages``, ``extend_unique``), reproducing the strings authored in the doc tables.
"""

from __future__ import annotations

import sys
from typing import Any, get_type_hints

from lg2m.ir import Attribute, DataModel


def model_from_class(cls: type, *, is_graph_state: bool) -> DataModel:
    """Build an ``ir.DataModel`` from a live state/payload class."""
    if hasattr(cls, "model_fields"):  # pydantic BaseModel (duck-typed)
        attributes = _pydantic_attributes(cls)
        style = "BaseModel"
    else:  # TypedDict or a plain annotated class
        attributes = _annotated_attributes(cls)
        style = "TypedDict"
    return DataModel(
        name=cls.__name__,
        style=style,
        is_graph_state=is_graph_state,
        attributes=attributes,
    )


def _annotated_attributes(cls: type) -> tuple[Attribute, ...]:
    hints = get_type_hints(cls, include_extras=True)
    out: list[Attribute] = []
    for name, hint in hints.items():
        if hasattr(hint, "__metadata__"):  # Annotated[base, reducer, ...]
            base = hint.__origin__
            reducer = _first_reducer(hint.__metadata__)
        else:
            base, reducer = hint, None
        out.append(Attribute(name=name, type_str=_type_name(base), reducer=reducer))
    return tuple(out)


def _pydantic_attributes(cls: Any) -> tuple[Attribute, ...]:
    return tuple(
        Attribute(name=name, type_str=_type_name(field.annotation))
        for name, field in cls.model_fields.items()
    )


def _first_reducer(metadata: tuple[Any, ...]) -> str | None:
    for extra in metadata:
        if callable(extra):
            return _reducer_name(extra)
    return None


def _reducer_name(fn: Any) -> str:
    """Best-effort public name of a reducer (name-level matching, docs/design.md Section 12).

    ``operator`` builtins are module-qualified (``operator.add``). Everything else uses the
    name the function is *bound to* in its defining module, preferring a public binding — so
    langgraph's ``add_messages`` (whose ``__name__`` is the private ``_add_messages``) reads
    as ``add_messages``, matching the doc tables.
    """
    module = getattr(fn, "__module__", "")
    raw = getattr(fn, "__name__", None) or repr(fn)
    if module in {"operator", "_operator"}:
        return f"operator.{raw}"
    return _public_binding(fn, module) or raw


def _public_binding(fn: Any, module: str) -> str | None:
    mod = sys.modules.get(module)
    if mod is None:
        return None
    names = [name for name, value in vars(mod).items() if value is fn]
    public = [name for name in names if not name.startswith("_")]
    return next(iter(public or names), None)


def _type_name(tp: Any) -> str:
    return getattr(tp, "__name__", None) or str(tp)
