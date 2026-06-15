"""Layer 2b Phase 3/4: assemble + canonicalize the doc and code sides.

The doc side runs the real ``support_pipeline.md`` through the fork/join + subgraph
canonicalizer; the result must equal the canonical topology vocabulary the Fake
also authors (Phase 4). Both sides agreeing is what makes the clean oracle empty.
"""

from __future__ import annotations

from _oracle import load_oracle_registry, oracle_topology
from lg2m.diff.assemble import END_ID, START_ID, assemble_code_model, assemble_doc_model
from lg2m.ir import GraphModel, Node, NodeKind
from lg2m.parsing import markdown
from lg2m.pipeline import gather_annotations

CANONICAL_NODES = {
    START_ID,
    "ingest_ticket",
    "fetch_history",
    "lookup_account",
    "classify_intent",
    "auto_resolve",
    "escalate_to_human",
    "investigate:gather_logs",
    "investigate:analyze",
    "map_items",
    "process_item",
    "reduce_items",
    "compose_reply",
    END_ID,
}

# (src, dst, predicate) — Edge identity
CANONICAL_EDGES = {
    (START_ID, "ingest_ticket", None),
    ("ingest_ticket", "fetch_history", None),
    ("ingest_ticket", "lookup_account", None),
    ("fetch_history", "classify_intent", None),
    ("lookup_account", "classify_intent", None),
    ("classify_intent", "escalate_to_human", "should_escalate"),
    ("classify_intent", "auto_resolve", "should_auto_resolve"),
    ("classify_intent", "investigate:gather_logs", "[else]"),
    ("investigate:gather_logs", "investigate:analyze", None),
    ("investigate:analyze", "map_items", None),
    ("map_items", "process_item", None),
    ("process_item", "reduce_items", None),
    ("reduce_items", "compose_reply", None),
    ("auto_resolve", "compose_reply", None),
    ("escalate_to_human", "compose_reply", None),
    ("compose_reply", END_ID, None),
}


def _doc_model(golden_md_text):
    doc = markdown.parse_markdown(golden_md_text, file="support_pipeline.md")
    return assemble_doc_model(doc, file="support_pipeline.md")


def test_doc_canonical_nodes(golden_md_text):
    gm = _doc_model(golden_md_text)
    assert set(gm.nodes) == CANONICAL_NODES
    assert gm.nodes[START_ID].kind is NodeKind.START
    assert gm.nodes[END_ID].kind is NodeKind.END
    # the diagram's pseudostates and composite are gone after canonicalization
    assert "fork_enrich" not in gm.nodes
    assert "join_enrich" not in gm.nodes
    assert "investigate" not in gm.nodes


def test_doc_canonical_edges(golden_md_text):
    gm = _doc_model(golden_md_text)
    assert {(e.src_id, e.dst_id, e.predicate) for e in gm.edges} == CANONICAL_EDGES


def test_doc_edge_flags(golden_md_text):
    gm = _doc_model(golden_md_text)
    by_id = {(e.src_id, e.dst_id, e.predicate): e for e in gm.edges}

    else_edge = by_id[("classify_intent", "investigate:gather_logs", "[else]")]
    assert else_edge.conditional and else_edge.is_else

    # Edges-table kind=send makes this conditional even though the arrow is plain
    send_edge = by_id[("map_items", "process_item", None)]
    assert send_edge.conditional

    # fork/join collapsed to parallel edges
    assert by_id[("ingest_ticket", "fetch_history", None)].parallel
    assert by_id[("fetch_history", "classify_intent", None)].parallel


def test_doc_routes(golden_md_text):
    gm = _doc_model(golden_md_text)
    assert set(gm.routes) == {"classify_intent"}
    route = gm.routes["classify_intent"]
    assert route.branches == (
        ("should_escalate", "escalate_to_human"),
        ("should_auto_resolve", "auto_resolve"),
    )
    assert route.else_target == "investigate"  # logical name, not the flattened entry
    assert route.loc is not None


def test_doc_models_and_predicates(golden_md_text):
    gm = _doc_model(golden_md_text)
    assert set(gm.models) == {"PipelineState", "Ticket"}
    assert gm.state_model_name == "PipelineState"

    state = gm.models["PipelineState"]
    assert {a.name: a.reducer for a in state.attributes} == {
        "ticket": None,
        "messages": "add_messages",
        "attempts": "operator.add",
        "enrichment": "operator.add",
        "flags": None,
        "items": None,
        "item_results": "extend_unique",
        "resolution": None,
    }
    assert set(gm.predicates) == {"should_escalate", "should_auto_resolve"}


def test_doc_has_no_diagnostics(golden_md_text):
    gm = _doc_model(golden_md_text)
    assert gm.diagnostics == []


def test_doc_node_locations_point_into_markdown(golden_md_text):
    gm = _doc_model(golden_md_text)
    assert gm.nodes["ingest_ticket"].loc is not None
    # the flattened subgraph node is located via its `### gather_logs` heading
    assert gm.nodes["investigate:gather_logs"].loc is not None


# --- Phase 4: the hand-authored oracle topology + code-side assembly ----------


def test_oracle_topology_equals_canonical_sets():
    topo = oracle_topology()
    assert set(topo.nodes) == CANONICAL_NODES
    assert {(e.src_id, e.dst_id, e.predicate) for e in topo.edges} == CANONICAL_EDGES


def test_code_model_nodes_and_anno_ids(golden_src_dir):
    reg, locations = load_oracle_registry(golden_src_dir)
    code = assemble_code_model(oracle_topology(), reg, locations)

    assert set(code.nodes) == CANONICAL_NODES
    # every real node carries an @node; the subgraph node maps by suffix
    assert code.nodes["ingest_ticket"].anno_id == "ingest_ticket"
    assert code.nodes["investigate:gather_logs"].anno_id == "gather_logs"
    assert code.nodes["investigate:analyze"].anno_id == "analyze"
    # sentinels carry no annotation
    assert code.nodes[START_ID].anno_id is None
    assert code.nodes[END_ID].anno_id is None
    # the @node decorator line came from the real file
    assert code.nodes["ingest_ticket"].loc is not None
    assert code.nodes["ingest_ticket"].loc.file.endswith("nodes.py")


def test_code_model_routes_predicates_models(golden_src_dir):
    reg, locations = load_oracle_registry(golden_src_dir)
    code = assemble_code_model(oracle_topology(), reg, locations)

    route = code.routes["classify_intent"]
    assert route.branches == (
        ("should_escalate", "escalate_to_human"),
        ("should_auto_resolve", "auto_resolve"),
    )
    assert route.else_target == "investigate"
    assert route.loc is not None and route.loc.file.endswith("routing.py")

    assert set(code.predicates) == {"should_escalate", "should_auto_resolve"}
    assert set(code.models) == {"PipelineState", "Ticket"}
    assert code.state_model_name == "PipelineState"
    assert code.models["PipelineState"].style == "TypedDict"


def test_code_model_carries_node_and_predicate_docstrings(tmp_path):
    """Layer 6 Task 2.2: gather_annotations + assemble_code_model thread docstrings to the IR."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text(
        'from lg2m import node, predicate\n'
        '@node("n")\n'
        'def n(state):\n'
        '    """Node prose here."""\n'
        '    return state\n'
        '@predicate("p")\n'
        'def p(state):\n'
        '    """Predicate prose here."""\n'
        '    return True\n',
        encoding="utf-8",
    )
    registry, locations = gather_annotations(pkg)
    topo = GraphModel(graph_id="t", origin="code")
    topo.nodes["n"] = Node(id="n")
    code = assemble_code_model(topo, registry, locations)

    assert code.nodes["n"].docstring == "Node prose here."
    assert code.predicates["p"].docstring == "Predicate prose here."
