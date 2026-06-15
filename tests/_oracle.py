"""Hand-authored canonical oracle for the support_pipeline graph (framework-free).

Stands in for what ``get_graph(xray=True)`` + state-schema introspection WOULD
yield, so the diff engine runs end-to-end without importing langgraph. The topology
is authored in canonical vocabulary and MUST equal the canonicalized diagram (see
``tests/test_assemble.py``). The registry is recovered from the real annotated
source with the AST reader (no import), so the code side is derived from the real
files even though the modules cannot be imported in the dev venv.

This module is intentionally not named ``test_*`` so pytest does not collect it.
"""

from __future__ import annotations

from pathlib import Path

from lg2m.annotations import reader
from lg2m.annotations.registry import (
    ModelEntry,
    NodeEntry,
    PredicateEntry,
    Registry,
    RouterEntry,
    get_registry,
)
from lg2m.diff.assemble import END_ID, START_ID
from lg2m.ir import Attribute, DataModel, Edge, GraphModel, Node, NodeKind, SourceLocation

_NODE_IDS = (
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
)


def _edge(src, dst, predicate=None, *, conditional=False, is_else=False, parallel=False) -> Edge:
    return Edge(src, dst, predicate, conditional=conditional, is_else=is_else, parallel=parallel)


def _pipeline_state() -> DataModel:
    attrs = (
        Attribute("ticket", "Ticket"),
        Attribute("messages", "list", "add_messages"),
        Attribute("attempts", "int", "operator.add"),
        Attribute("enrichment", "list", "operator.add"),
        Attribute("flags", "dict"),
        Attribute("items", "list"),
        Attribute("item_results", "list", "extend_unique"),
        Attribute("resolution", "str"),
    )
    return DataModel(name="PipelineState", style="TypedDict", is_graph_state=True, attributes=attrs)


def _ticket() -> DataModel:
    attrs = (
        Attribute("subject", "str"),
        Attribute("body", "str"),
        Attribute("priority", "str"),
        Attribute("customer_tier", "str"),
    )
    return DataModel(name="Ticket", style="BaseModel", is_graph_state=False, attributes=attrs)


def oracle_topology() -> GraphModel:
    """The canonical code-side topology: 14 nodes, 16 edges, two models."""
    gm = GraphModel(graph_id="support_pipeline", origin="code")
    gm.nodes[START_ID] = Node(id=START_ID, kind=NodeKind.START)
    gm.nodes[END_ID] = Node(id=END_ID, kind=NodeKind.END)
    for nid in _NODE_IDS:
        gm.nodes[nid] = Node(id=nid, kind=NodeKind.NODE)

    gm.edges.extend(
        [
            _edge(START_ID, "ingest_ticket"),
            _edge("ingest_ticket", "fetch_history", parallel=True),
            _edge("ingest_ticket", "lookup_account", parallel=True),
            _edge("fetch_history", "classify_intent", parallel=True),
            _edge("lookup_account", "classify_intent", parallel=True),
            _edge("classify_intent", "escalate_to_human", "should_escalate", conditional=True),
            _edge("classify_intent", "auto_resolve", "should_auto_resolve", conditional=True),
            _edge("classify_intent", "investigate:gather_logs", "[else]",
                  conditional=True, is_else=True),
            _edge("investigate:gather_logs", "investigate:analyze"),
            _edge("investigate:analyze", "map_items"),
            _edge("map_items", "process_item", conditional=True),
            _edge("process_item", "reduce_items"),
            _edge("reduce_items", "compose_reply"),
            _edge("auto_resolve", "compose_reply"),
            # Command(goto) edge: get_graph reports it conditional (predicate is None).
            _edge("escalate_to_human", "compose_reply", conditional=True),
            _edge("compose_reply", END_ID),
        ]
    )

    gm.models["PipelineState"] = _pipeline_state()
    gm.models["Ticket"] = _ticket()
    gm.state_model_name = "PipelineState"
    return gm


def _stub(*_args, **_kwargs):  # registry targets the diff never calls
    return None


def load_oracle_registry(
    src_dir: Path,
) -> tuple[Registry, dict[tuple[str, str], SourceLocation]]:
    """Populate the live registry from the real annotated files via the AST reader.

    Returns the registry and a ``(kind, key) -> SourceLocation`` map that also carries
    ``("router", source)`` keys, the shape ``assemble_code_model`` consumes.
    """
    reg = get_registry()
    locations: dict[tuple[str, str], SourceLocation] = {}
    for fname in ("state.py", "predicates.py", "routing.py", "nodes.py"):
        result = reader.read_file(src_dir / fname)
        for ref in result.annotations:
            if ref.kind == "node":
                reg.nodes[ref.key] = NodeEntry(ref.key, _stub, None, ref.loc.line)
            elif ref.kind == "predicate":
                reg.predicates[ref.key] = PredicateEntry(ref.key, _stub, None, ref.loc.line)
            elif ref.kind in ("state_model", "data_model"):
                reg.models[ref.key] = ModelEntry(
                    ref.key, object, ref.kind == "state_model", None, ref.loc.line
                )
        for route in result.routers:
            reg.routers[route.source_id] = RouterEntry(
                route.source_id, route.branches, route.else_target or "", _stub, None,
                route.loc.line,
            )
            locations[("router", route.source_id)] = route.loc
        locations.update(reader.merge_locations(result, reg))
    return reg, locations
