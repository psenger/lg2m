"""Layer 2b Phase 5: reconcile() — the clean oracle and one drift per category."""

from __future__ import annotations

from _oracle import load_oracle_registry, oracle_topology
from lg2m.diff.assemble import assemble_code_model, assemble_doc_model
from lg2m.diff.categories import DriftCategory
from lg2m.diff.engine import reconcile
from lg2m.ir import (
    Attribute,
    DataModel,
    Diagnostic,
    DiagnosticKind,
    Edge,
    GraphModel,
    Meta,
    MetaKind,
    Node,
    Predicate,
    Route,
)
from lg2m.parsing import markdown


def _categories(report):
    return {i.category for i in report.items}


def _node(nid, **kw):
    return Node(id=nid, **kw)


# --- the headline: all three sources agree -> empty report -------------------


def _assemble_clean(golden_md_text, golden_src_dir):
    doc = assemble_doc_model(
        markdown.parse_markdown(golden_md_text, file="support_pipeline.md"),
        file="support_pipeline.md",
    )
    registry, locations = load_oracle_registry(golden_src_dir)
    code = assemble_code_model(oracle_topology(), registry, locations)
    return code, doc


def test_clean_oracle_reconciles_empty(golden_md_text, golden_src_dir):
    code, doc = _assemble_clean(golden_md_text, golden_src_dir)
    report = reconcile(code, doc)
    assert report.items == [], [f"{i.category.value}: {i.message}" for i in report.items]
    assert report.is_clean
    assert report.exit_code == 0


# --- docs/design.md Section 9 drift cases ----------------------------------------------


def test_section9_route_target_rename(golden_md_text, golden_src_dir):
    code, doc = _assemble_clean(golden_md_text, golden_src_dir)
    original = code.routes["classify_intent"]
    code.routes["classify_intent"] = Route(
        "classify_intent",
        (("should_escalate", "HUMAN_AGENT"), ("should_auto_resolve", "auto_resolve")),
        "investigate",
        loc=original.loc,
    )
    report = reconcile(code, doc)
    assert DriftCategory.ROUTE_TARGET_MISMATCH in _categories(report)
    item = next(i for i in report.items if i.category is DriftCategory.ROUTE_TARGET_MISMATCH)
    assert item.code_loc is not None and item.doc_loc is not None


def test_section9_missing_else(golden_md_text, golden_src_dir):
    code, doc = _assemble_clean(golden_md_text, golden_src_dir)
    route = doc.routes["classify_intent"]
    doc.routes["classify_intent"] = Route(
        "classify_intent", route.branches, None, loc=route.loc
    )
    report = reconcile(code, doc)
    assert DriftCategory.MISSING_ELSE in _categories(report)


# --- one drift per category (hand-built minimal pairs) -----------------------


def test_node_missing_in_doc():
    code = GraphModel("g", "code")
    code.nodes.update({"a": _node("a", anno_id="a"), "b": _node("b", anno_id="b")})
    doc = GraphModel("g", "markdown", nodes={"a": _node("a")})
    report = reconcile(code, doc)
    assert _categories(report) == {DriftCategory.NODE_MISSING_IN_DOC}
    assert report.exit_code == 1


def test_node_missing_in_code():
    code = GraphModel("g", "code", nodes={"a": _node("a", anno_id="a")})
    doc = GraphModel("g", "markdown", nodes={"a": _node("a"), "z": _node("z")})
    assert DriftCategory.NODE_MISSING_IN_CODE in _categories(reconcile(code, doc))


def test_annotation_node_mismatch():
    code = GraphModel("g", "code", nodes={"a": _node("a")})  # no anno_id
    doc = GraphModel("g", "markdown", nodes={"a": _node("a")})
    assert _categories(reconcile(code, doc)) == {DriftCategory.ANNOTATION_NODE_MISMATCH}


def test_edge_missing_in_doc():
    nodes = {"a": _node("a", anno_id="a"), "b": _node("b", anno_id="b")}
    code = GraphModel("g", "code", nodes=dict(nodes), edges=[Edge("a", "b")])
    doc = GraphModel("g", "markdown", nodes=dict(nodes))
    assert _categories(reconcile(code, doc)) == {DriftCategory.EDGE_MISSING_IN_DOC}


def test_edge_conditionality_mismatch():
    nodes = {"a": _node("a", anno_id="a"), "b": _node("b", anno_id="b")}
    code = GraphModel("g", "code", nodes=dict(nodes), edges=[Edge("a", "b", conditional=True)])
    doc = GraphModel("g", "markdown", nodes=dict(nodes), edges=[Edge("a", "b", conditional=False)])
    assert DriftCategory.EDGE_CONDITIONALITY_MISMATCH in _categories(reconcile(code, doc))


def test_edge_label_mismatch():
    nodes = {"a": _node("a", anno_id="a"), "b": _node("b", anno_id="b")}
    code = GraphModel("g", "code", nodes=dict(nodes),
                      edges=[Edge("a", "b", "p1", conditional=True)])
    doc = GraphModel("g", "markdown", nodes=dict(nodes),
                     edges=[Edge("a", "b", "p2", conditional=True)])
    assert _categories(reconcile(code, doc)) == {DriftCategory.EDGE_LABEL_MISMATCH}


def test_predicate_undefined():
    nodes = {
        "a": _node("a", anno_id="a"),
        "b": _node("b", anno_id="b"),
        "c": _node("c", anno_id="c"),
    }
    edges = [
        Edge("a", "b", "p", conditional=True),
        Edge("a", "c", "[else]", conditional=True, is_else=True),
    ]
    route = {"a": Route("a", (("p", "b"),), "c")}
    code = GraphModel("g", "code", nodes=dict(nodes), edges=list(edges), routes=dict(route))
    doc = GraphModel("g", "markdown", nodes=dict(nodes), edges=list(edges), routes=dict(route))
    assert DriftCategory.PREDICATE_UNDEFINED in _categories(reconcile(code, doc))


def test_router_not_wired():
    nodes = {"a": _node("a", anno_id="a"), "b": _node("b", anno_id="b")}
    route = {"a": Route("a", (("p", "b"),), "b")}
    code = GraphModel("g", "code", nodes=dict(nodes), routes=dict(route),
                      predicates={"p": Predicate("p")})
    doc = GraphModel("g", "markdown", nodes=dict(nodes), routes=dict(route),
                     predicates={"p": Predicate("p")})
    assert DriftCategory.ROUTER_NOT_WIRED in _categories(reconcile(code, doc))


def test_predicate_missing_each_way():
    code = GraphModel("g", "code", predicates={"p": Predicate("p")})
    doc = GraphModel("g", "markdown", predicates={"q": Predicate("q")})
    cats = _categories(reconcile(code, doc))
    assert DriftCategory.PREDICATE_MISSING_IN_DOC in cats
    assert DriftCategory.PREDICATE_MISSING_IN_CODE in cats


def test_model_missing_and_attr_drift():
    code_model = DataModel("M", "TypedDict", attributes=(
        Attribute("x", "int", "operator.add"), Attribute("only_code", "str"),
    ))
    doc_model = DataModel("M", "", attributes=(
        Attribute("x", "str", "add_messages"), Attribute("only_doc", "str"),
    ))
    code = GraphModel("g", "code")
    code.models.update({"M": code_model, "Extra": DataModel("Extra", "BaseModel")})
    doc = GraphModel("g", "markdown", models={"M": doc_model})
    cats = _categories(reconcile(code, doc))
    assert DriftCategory.MODEL_MISSING_IN_DOC in cats          # Extra only in code
    assert DriftCategory.ATTR_TYPE_DRIFT in cats               # x: int vs str
    assert DriftCategory.ATTR_REDUCER_DRIFT in cats            # x: operator.add vs add_messages
    assert DriftCategory.ATTR_MISSING_IN_DOC in cats           # only_code
    assert DriftCategory.ATTR_MISSING_IN_CODE in cats          # only_doc


def test_state_model_mismatch():
    code = GraphModel("g", "code", state_model_name="A")
    doc = GraphModel("g", "markdown", state_model_name="B")
    assert _categories(reconcile(code, doc)) == {DriftCategory.STATE_MODEL_MISMATCH}


def test_meta_drift_command_goto_without_edge():
    nodes = {"n": _node("n", anno_id="n"), "compose": _node("compose", anno_id="compose")}
    code = GraphModel("g", "code", nodes=dict(nodes))  # no n -> compose edge
    doc = GraphModel("g", "markdown", nodes=dict(nodes),
                     meta=[Meta("n", MetaKind.FENCE, {"command_goto": "compose"})])
    assert DriftCategory.META_DRIFT in _categories(reconcile(code, doc))


def test_prose_drift_is_warning_only():
    code = GraphModel("g", "code", nodes={"n": _node("n", anno_id="n", docstring="alpha")})
    doc = GraphModel("g", "markdown", nodes={"n": _node("n", prose="beta")})
    report = reconcile(code, doc)
    assert _categories(report) == {DriftCategory.PROSE_DRIFT}
    assert report.exit_code == 0  # warning does not fail the build


def test_prose_drift_covers_predicates():
    """Layer 6 Task 2.3: _check_prose now reports predicate prose drift, not just nodes."""
    code = GraphModel("g", "code", predicates={"p": Predicate(name="p", docstring="alpha")})
    doc = GraphModel("g", "markdown", predicates={"p": Predicate(name="p", prose="beta")})
    assert _categories(reconcile(code, doc)) == {DriftCategory.PROSE_DRIFT}


def test_prose_normalization_no_false_drift():
    """Layer 6 Task 2.3: body-indented docstring vs column-0 prose is not drift."""
    code = GraphModel("g", "code",
                      nodes={"n": _node("n", anno_id="n", docstring="One.\n\n    Two.\n    ")})
    doc = GraphModel("g", "markdown", nodes={"n": _node("n", prose="One.\n\nTwo.")})
    assert _categories(reconcile(code, doc)) == set()


def test_diagnostics_fold_and_strict_escalation():
    doc = GraphModel("g", "markdown",
                     diagnostics=[Diagnostic(DiagnosticKind.NON_ENUMERABLE_TARGETS, "x", "m")])
    code = GraphModel("g", "code")
    assert reconcile(code, doc).exit_code == 0           # warning by default
    assert reconcile(code, doc, strict=True).exit_code == 1  # strict escalates to error


def test_missing_else_diagnostic_is_error():
    doc = GraphModel("g", "markdown",
                     diagnostics=[Diagnostic(DiagnosticKind.MISSING_ELSE, "classify", "no else")])
    report = reconcile(GraphModel("g", "code"), doc)
    assert DriftCategory.MISSING_ELSE in _categories(report)
    assert report.exit_code == 1
