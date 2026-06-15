"""AC-01..AC-04, AC-12: the authoring decorators record metadata and return the target."""

from __future__ import annotations

import pytest

from lg2m.annotations import decorators
from lg2m.annotations.registry import get_registry


def test_node_records_and_returns_unchanged():
    """AC-01."""

    @decorators.node("ingest_ticket")
    def ingest_ticket(state):
        return {"seen": state}

    reg = get_registry()
    assert reg.nodes["ingest_ticket"].target is ingest_ticket
    assert ingest_ticket("x") == {"seen": "x"}  # returned unchanged, still callable


def test_predicate_records_and_returns_unchanged():
    """AC-02."""

    @decorators.predicate("should_escalate")
    def should_escalate(state):
        return bool(state)

    reg = get_registry()
    assert reg.predicates["should_escalate"].target is should_escalate
    assert should_escalate(True) is True


def test_data_model_bare_records_not_graph_state():
    """AC-03."""

    @decorators.data_model
    class Ticket:
        pass

    entry = get_registry().models["Ticket"]
    assert entry.is_graph_state is False
    assert entry.target is Ticket
    assert isinstance(Ticket(), Ticket)  # returned unchanged, still constructible


def test_state_model_bare_records_graph_state():
    """AC-04."""

    @decorators.state_model
    class PipelineState(dict):
        pass

    assert get_registry().models["PipelineState"].is_graph_state is True


def test_predicate_named_else_is_rejected():
    """AC-12."""
    with pytest.raises(ValueError, match=r"\[else\]"):
        decorators.predicate("[else]")


def test_node_empty_id_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        decorators.node("")


def test_decorator_records_module_and_line():
    @decorators.node("n")
    def n(state):
        return state

    entry = get_registry().nodes["n"]
    assert entry.module == __name__
    assert isinstance(entry.lineno, int)
