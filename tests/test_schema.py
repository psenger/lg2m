"""Layer 3 Phase 2: framework-free model_from_class (no langgraph/pydantic import)."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from lg2m.introspect.schema import model_from_class


def _custom_reducer(left, right):
    return left


class _State(TypedDict):
    ticket: str
    messages: Annotated[list, operator.add]
    flags: dict
    item_results: Annotated[list, _custom_reducer]


def test_typeddict_attributes_types_and_reducers():
    dm = model_from_class(_State, is_graph_state=True)
    assert dm.name == "_State"
    assert dm.style == "TypedDict"
    assert dm.is_graph_state is True
    assert {(a.name, a.type_str, a.reducer) for a in dm.attributes} == {
        ("ticket", "str", None),
        ("messages", "list", "operator.add"),  # operator module -> qualified
        ("flags", "dict", None),
        ("item_results", "list", "_custom_reducer"),  # else -> __name__
    }


def test_attribute_order_is_definition_order():
    dm = model_from_class(_State, is_graph_state=True)
    assert [a.name for a in dm.attributes] == ["ticket", "messages", "flags", "item_results"]


class _FakeField:
    def __init__(self, annotation):
        self.annotation = annotation


class _FakeBaseModel:
    """Duck-typed pydantic stand-in (so this test imports no framework)."""

    model_fields = {"subject": _FakeField(str), "priority": _FakeField(str)}


def test_pydantic_path_reads_model_fields():
    dm = model_from_class(_FakeBaseModel, is_graph_state=False)
    assert dm.style == "BaseModel"
    assert dm.is_graph_state is False
    assert {(a.name, a.type_str, a.reducer) for a in dm.attributes} == {
        ("subject", "str", None),
        ("priority", "str", None),
    }
