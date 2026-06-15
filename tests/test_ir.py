"""AC-16: the IR value objects enforce identity structurally."""

from __future__ import annotations

import dataclasses

import pytest

from lg2m.ir import (
    DataModel,
    Edge,
    GraphModel,
    Meta,
    MetaKind,
    Node,
    NodeKind,
    Predicate,
    Route,
    SourceLocation,
)


def test_edge_identity_is_src_dst_predicate():
    a = Edge("classify_intent", "escalate_to_human", "should_escalate")
    b = Edge("classify_intent", "escalate_to_human", "should_escalate")
    assert a == b
    assert hash(a) == hash(b)
    # non-identity fields do not affect equality
    c = Edge("classify_intent", "escalate_to_human", "should_escalate",
             conditional=True, is_else=False, loc=SourceLocation("x.md", 1))
    assert a == c
    assert hash(a) == hash(c)


def test_two_predicates_to_same_target_are_distinct_edges():
    e1 = Edge("classify_intent", "compose_reply", "should_escalate")
    e2 = Edge("classify_intent", "compose_reply", "should_auto_resolve")
    assert e1 != e2
    assert len({e1, e2}) == 2


def test_unconditional_edge_predicate_is_none():
    e = Edge("fork_enrich", "fetch_history")
    assert e.predicate is None
    assert e == Edge("fork_enrich", "fetch_history")


def test_else_branch_is_distinct_identity():
    branch = Edge("classify_intent", "auto_resolve", "should_auto_resolve")
    default = Edge("classify_intent", "investigate", "[else]", is_else=True, conditional=True)
    assert branch != default
    assert default.predicate == "[else]"
    assert default.is_else is True


def test_node_identity_is_id_only():
    n1 = Node("investigate", kind=NodeKind.NODE, is_subgraph=True, prose="a")
    n2 = Node("investigate", kind=NodeKind.NODE, is_subgraph=False, prose="b",
              meta={"pseudostate": "x"})
    assert n1 == n2
    assert hash(n1) == hash(n2)
    assert len({n1, n2}) == 1


def test_predicate_identity_is_name():
    assert Predicate("should_escalate", prose="p") == Predicate("should_escalate")
    assert Predicate("should_escalate") != Predicate("should_auto_resolve")


def test_value_objects_are_frozen():
    for obj in (
        Node("a"),
        Edge("a", "b"),
        Predicate("p"),
        Route("a", (("p", "b"),), "c"),
        Meta("a", MetaKind.NOTE, "text"),
        SourceLocation("x.md", 1),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            obj.loc = None  # type: ignore[misc]


def test_route_and_datamodel_are_hashable():
    r = Route("classify_intent", (("should_escalate", "escalate_to_human"),), "investigate")
    assert hash(r) == hash(
        Route("classify_intent", (("should_escalate", "escalate_to_human"),), "investigate")
    )
    dm = DataModel("Ticket", "BaseModel")
    assert hash(dm) == hash(DataModel("Ticket", "BaseModel"))


def test_graphmodel_is_a_mutable_assembly_buffer():
    gm = GraphModel("support_pipeline", origin="markdown")
    gm.nodes["a"] = Node("a")
    gm.edges.append(Edge("a", "b"))
    assert gm.graph_id == "support_pipeline"
    assert "a" in gm.nodes
    assert gm.edges[0].src_id == "a"
