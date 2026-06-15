"""Mermaid parse/emit: AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-15."""

from __future__ import annotations

import pytest

from lg2m.parsing import markdown, mermaid

EXPECTED_STATES = {
    "ingest_ticket", "fork_enrich", "join_enrich", "fetch_history", "lookup_account",
    "classify_intent", "escalate_to_human", "auto_resolve", "investigate", "gather_logs",
    "analyze", "map_items", "process_item", "reduce_items", "compose_reply",
}


@pytest.fixture
def diagram(golden_md_text):
    lines = markdown.parse_markdown(golden_md_text).mermaid_lines
    return mermaid.parse_mermaid(lines, file="support_pipeline.md")


def test_no_parse_diagnostics(diagram):
    assert diagram.diagnostics == []


def test_named_states(diagram):
    """AC-05: exactly the 15 named states; [*] is not one."""
    assert set(diagram.named_state_ids) == EXPECTED_STATES
    assert len(diagram.named_state_ids) == 15
    assert "[*]" not in diagram.states


def test_fork_join_pseudostates(diagram):
    """AC-06."""
    assert diagram.states["fork_enrich"].pseudostate == "fork"
    assert diagram.states["join_enrich"].pseudostate == "join"
    assert diagram.states["fork_enrich"].is_subgraph is False
    assert diagram.states["join_enrich"].is_subgraph is False


def test_conditional_fanout_and_route(diagram):
    """AC-07."""
    cond = [e for e in diagram.edges if e.src == "classify_intent" and e.conditional]
    assert len(cond) == 3
    assert {(e.predicate, e.dst, e.is_else) for e in cond} == {
        ("should_escalate", "escalate_to_human", False),
        ("should_auto_resolve", "auto_resolve", False),
        ("[else]", "investigate", True),
    }

    routes = mermaid.derive_routes(diagram)
    assert set(routes) == {"classify_intent"}
    route = routes["classify_intent"]
    assert route.branches == (
        ("should_escalate", "escalate_to_human"),
        ("should_auto_resolve", "auto_resolve"),
    )
    assert route.else_target == "investigate"


def test_composite_subgraph(diagram):
    """AC-08."""
    assert diagram.states["investigate"].is_subgraph is True
    internal = [(e.src, e.dst) for e in diagram.edges if e.scope == "investigate"]
    assert internal == [("[*]", "gather_logs"), ("gather_logs", "analyze"), ("analyze", "[*]")]
    # the subgraph's nodes carry investigate as parent
    assert diagram.states["gather_logs"].parent == "investigate"
    assert diagram.states["analyze"].parent == "investigate"


def test_start_end_by_position_and_scope(diagram):
    """AC-09."""
    top_starts = [e for e in diagram.edges if e.src == "[*]" and e.scope is None]
    top_ends = [e for e in diagram.edges if e.dst == "[*]" and e.scope is None]
    assert [e.dst for e in top_starts] == ["ingest_ticket"]
    assert [e.src for e in top_ends] == ["compose_reply"]

    sub_starts = [e for e in diagram.edges if e.src == "[*]" and e.scope == "investigate"]
    sub_ends = [e for e in diagram.edges if e.dst == "[*]" and e.scope == "investigate"]
    assert [e.dst for e in sub_starts] == ["gather_logs"]
    assert [e.src for e in sub_ends] == ["analyze"]


def test_send_and_command_edges_are_plain(diagram):
    """AC-10: Send/Command nature is metadata, not diagram syntax."""
    for src, dst in (("map_items", "process_item"), ("escalate_to_human", "compose_reply")):
        edge = next(e for e in diagram.edges if e.src == src and e.dst == dst)
        assert edge.predicate is None
        assert edge.conditional is False
        assert edge.is_else is False


def test_total_edge_count(diagram):
    top = [e for e in diagram.edges if e.scope is None]
    internal = [e for e in diagram.edges if e.scope == "investigate"]
    assert len(top) == 17
    assert len(internal) == 3
    assert len(diagram.edges) == 20


def _structural_key(d):
    states = {sid: (s.is_subgraph, s.pseudostate) for sid, s in d.states.items()}
    edges = [(e.src, e.dst, e.predicate, e.is_else, e.conditional, e.scope) for e in d.edges]
    return states, edges


def test_structural_round_trip(diagram):
    """AC-15: parse(block) == parse(emit(parse(block))) on structural fields."""
    reparsed = mermaid.parse_mermaid(mermaid.emit_mermaid(diagram))
    assert reparsed.diagnostics == []
    assert _structural_key(diagram) == _structural_key(reparsed)
