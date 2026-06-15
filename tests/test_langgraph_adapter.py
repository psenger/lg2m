"""Layer 3 Phase 3: the adapter translates the REAL compiled graph into canonical IR.

Marked ``@pytest.mark.langgraph`` (imports the framework). Verifies the assumptions the
layer-2b Fake was authored against — most importantly that a Model-A conditional edge's
``.data`` is the predicate name.
"""

from __future__ import annotations

import pytest

from lg2m.annotations.registry import ModelEntry, Registry
from lg2m.introspect.langgraph_adapter import LangGraphIntrospector
from lg2m.ir import NodeKind
from test_assemble import CANONICAL_EDGES, CANONICAL_NODES

pytestmark = pytest.mark.langgraph


def _registry_with_models() -> Registry:
    from support_pipeline.state import PipelineState, Ticket

    reg = Registry()
    reg.models["PipelineState"] = ModelEntry("PipelineState", PipelineState, True, None, None)
    reg.models["Ticket"] = ModelEntry("Ticket", Ticket, False, None, None)
    return reg


def _topology(golden_compiled):
    adapter = LangGraphIntrospector(golden_compiled, registry=_registry_with_models())
    return adapter.introspect("support_pipeline")


def test_adapter_nodes_match_canonical(golden_compiled):
    topo = _topology(golden_compiled)
    assert set(topo.nodes) == CANONICAL_NODES
    assert topo.nodes["__start__"].kind is NodeKind.START
    assert topo.nodes["__end__"].kind is NodeKind.END


def test_adapter_edges_match_canonical(golden_compiled):
    topo = _topology(golden_compiled)
    assert {(e.src_id, e.dst_id, e.predicate) for e in topo.edges} == CANONICAL_EDGES


def test_adapter_conditional_labels_are_predicate_names(golden_compiled):
    topo = _topology(golden_compiled)
    by = {(e.src_id, e.dst_id): e for e in topo.edges}

    assert by[("classify_intent", "escalate_to_human")].predicate == "should_escalate"
    assert by[("classify_intent", "auto_resolve")].predicate == "should_auto_resolve"
    els = by[("classify_intent", "investigate:gather_logs")]
    assert els.predicate == "[else]" and els.is_else

    # Command + Send edges: conditional, but no predicate label
    cmd = by[("escalate_to_human", "compose_reply")]
    assert cmd.conditional and cmd.predicate is None
    send = by[("map_items", "process_item")]
    assert send.conditional and send.predicate is None


def test_adapter_state_schema_and_reducers(golden_compiled):
    topo = _topology(golden_compiled)
    assert topo.state_model_name == "PipelineState"
    state = topo.models["PipelineState"]
    assert state.style == "TypedDict"
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


def test_adapter_payload_model_from_registry(golden_compiled):
    topo = _topology(golden_compiled)
    ticket = topo.models["Ticket"]
    assert ticket.style == "BaseModel"
    assert ticket.is_graph_state is False
    assert {a.name for a in ticket.attributes} == {"subject", "body", "priority", "customer_tier"}
    assert all(a.reducer is None for a in ticket.attributes)
