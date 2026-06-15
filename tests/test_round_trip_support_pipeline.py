"""Phase 4 acceptance gate: assemble the golden fixture into a GraphModel.

Wires markdown + tables + meta + mermaid into one ``GraphModel`` and asserts the
structural fields (AC-04/05/06/07/08/11/13/17/18), plus the mermaid structural
round-trip on the fixture block (AC-15).
"""

from __future__ import annotations

import pytest

from lg2m.ir import Attribute, DataModel, Edge, GraphModel, Node, NodeKind, Predicate
from lg2m.parsing import markdown, mermaid, tables
from lg2m.parsing import meta as meta_parser

EXPECTED_STATES = {
    "ingest_ticket", "fork_enrich", "join_enrich", "fetch_history", "lookup_account",
    "classify_intent", "escalate_to_human", "auto_resolve", "investigate", "gather_logs",
    "analyze", "map_items", "process_item", "reduce_items", "compose_reply",
}


def _strip_bt(text: str) -> str:
    return text.strip().strip("`").strip()


def _build_data_model(entity) -> DataModel:
    parsed = tables.parse_table(entity.lines)
    attributes: tuple[Attribute, ...] = ()
    if parsed is not None:
        _, rows = parsed
        attributes = tuple(
            Attribute(
                name=_strip_bt(r["attribute"]),
                type_str=_strip_bt(r["type"]),
                reducer=(None if r["reducer"].strip() == "-" else _strip_bt(r["reducer"])),
                description=r["description"],
            )
            for r in rows
        )
    return DataModel(
        name=entity.id,
        style="",  # code-side fact; populated by the later introspection layer
        is_graph_state="@state_model" in entity.prose,
        attributes=attributes,
        prose=entity.prose,
    )


def build_graph_model(text: str, *, file: str = "support_pipeline.md") -> GraphModel:
    doc = markdown.parse_markdown(text, file=file)
    diagram = mermaid.parse_mermaid(doc.mermaid_lines, file=file)
    gm = GraphModel(graph_id=doc.graph_id, origin="markdown")

    for sid, state in diagram.states.items():
        node_meta = {"pseudostate": state.pseudostate} if state.pseudostate else {}
        gm.nodes[sid] = Node(id=sid, kind=NodeKind.NODE, is_subgraph=state.is_subgraph,
                             meta=node_meta)

    for e in diagram.edges:
        gm.edges.append(
            Edge(src_id=e.src, dst_id=e.dst, predicate=e.predicate,
                 conditional=e.conditional, is_else=e.is_else)
        )

    gm.routes.update(mermaid.derive_routes(diagram))

    for entity in doc.entities:
        if entity.section == "Predicates":
            gm.predicates[entity.id] = Predicate(name=entity.id, prose=entity.prose)
        elif entity.section == "Data Models":
            dm = _build_data_model(entity)
            gm.models[dm.name] = dm
            if dm.is_graph_state:
                gm.state_model_name = dm.name
        gm.meta.extend(meta_parser.parse_entity_meta(entity.id, entity.lines))

    gm.diagnostics.extend(diagram.diagnostics)
    return gm


@pytest.fixture
def gm(golden_md_text) -> GraphModel:
    return build_graph_model(golden_md_text)


@pytest.fixture
def doc(golden_md_text):
    return markdown.parse_markdown(golden_md_text)


def test_graph_id_and_state_model(gm):
    """AC-04 + state model."""
    assert gm.graph_id == "support_pipeline"
    assert gm.state_model_name == "PipelineState"
    assert gm.diagnostics == []


def test_nodes(gm):
    """AC-05 + AC-06."""
    assert set(gm.nodes) == EXPECTED_STATES
    assert gm.nodes["investigate"].is_subgraph is True
    assert gm.nodes["fork_enrich"].meta["pseudostate"] == "fork"
    assert gm.nodes["join_enrich"].meta["pseudostate"] == "join"


def test_conditional_fanout_and_route(gm):
    """AC-07."""
    cond = [e for e in gm.edges if e.src_id == "classify_intent" and e.conditional]
    assert {(e.predicate, e.dst_id, e.is_else) for e in cond} == {
        ("should_escalate", "escalate_to_human", False),
        ("should_auto_resolve", "auto_resolve", False),
        ("[else]", "investigate", True),
    }
    assert set(gm.routes) == {"classify_intent"}
    route = gm.routes["classify_intent"]
    assert route.branches == (
        ("should_escalate", "escalate_to_human"),
        ("should_auto_resolve", "auto_resolve"),
    )
    assert route.else_target == "investigate"


def test_subgraph_internal_edges_present(gm):
    """AC-08 (flattened view): investigate is a subgraph and its 3 edges exist."""
    assert gm.nodes["investigate"].is_subgraph is True
    pairs = {(e.src_id, e.dst_id) for e in gm.edges}
    assert {("[*]", "gather_logs"), ("gather_logs", "analyze"), ("analyze", "[*]")} <= pairs


def test_data_models_and_reducers(gm):
    """AC-11."""
    assert set(gm.models) == {"PipelineState", "Ticket"}

    state = gm.models["PipelineState"]
    assert state.is_graph_state is True
    assert len(state.attributes) == 8
    reducers = {a.name: a.reducer for a in state.attributes}
    assert reducers == {
        "ticket": None,
        "messages": "add_messages",
        "attempts": "operator.add",
        "enrichment": "operator.add",
        "flags": None,
        "items": None,
        "item_results": "extend_unique",
        "resolution": None,
    }

    ticket = gm.models["Ticket"]
    assert ticket.is_graph_state is False
    assert len(ticket.attributes) == 4
    assert all(a.reducer is None for a in ticket.attributes)


def test_metadata_count(gm):
    """AC-13."""
    assert len(gm.meta) == 6


def test_index_table(doc):
    """AC-17."""
    _, rows = tables.parse_table(doc.sections["Index"].lines)
    assert len(rows) == 15
    node_ids = {_strip_bt(r["id"]) for r in rows if r["type"] == "node"}
    pred_ids = {_strip_bt(r["id"]) for r in rows if r["type"] == "predicate"}
    assert len(node_ids) == 13
    assert pred_ids == {"should_escalate", "should_auto_resolve"}
    # the diagram pseudostates are not Index node ids
    assert "fork_enrich" not in node_ids
    assert "join_enrich" not in node_ids


def test_edges_table(doc):
    """AC-18."""
    headers, rows = tables.parse_table(doc.sections["Edges"].lines)
    assert headers == ["from", "to", "label", "kind", "notes"]
    assert len(rows) == 17
    assert all(isinstance(r["label"], str) for r in rows)
    labelled = {r["label"] for r in rows if r["label"]}
    assert labelled == {"`should_escalate`", "`should_auto_resolve`", "`[else]`"}


def test_mermaid_round_trip_on_fixture(golden_md_text):
    """AC-15 against the fixture's actual block."""
    lines = markdown.parse_markdown(golden_md_text).mermaid_lines
    diagram = mermaid.parse_mermaid(lines)
    reparsed = mermaid.parse_mermaid(mermaid.emit_mermaid(diagram))
    assert reparsed.diagnostics == []

    def key(d):
        states = {sid: (s.is_subgraph, s.pseudostate) for sid, s in d.states.items()}
        edges = [(e.src, e.dst, e.predicate, e.is_else, e.conditional, e.scope) for e in d.edges]
        return states, edges

    assert key(diagram) == key(reparsed)
