"""Drift categories, severities, and the diagnostic-fold table (docs/design.md Section 8).

``DriftCategory`` names a CROSS-SOURCE reconciliation outcome (e.g. a node is in
code but not the doc). It is distinct from ``ir.DiagnosticKind``, which names a
SINGLE-SOURCE structural fact discovered during parse/introspect (e.g. a ``Command``
without ``destinations``). The two never merge: the engine FOLDS each parse /
introspect ``Diagnostic`` into a ``DriftItem`` via ``DIAGNOSTIC_MAP``, so there is
one report and one exit path while authorship of structural facts stays upstream.
"""

from __future__ import annotations

from enum import Enum

from lg2m.ir import DiagnosticKind


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class DriftCategory(str, Enum):
    # nodes
    NODE_MISSING_IN_DOC = "node_missing_in_doc"
    NODE_MISSING_IN_CODE = "node_missing_in_code"
    ANNOTATION_NODE_MISMATCH = "annotation_node_mismatch"
    # edges
    EDGE_MISSING_IN_DOC = "edge_missing_in_doc"
    EDGE_MISSING_IN_CODE = "edge_missing_in_code"
    EDGE_CONDITIONALITY_MISMATCH = "edge_conditionality_mismatch"
    EDGE_LABEL_MISMATCH = "edge_label_mismatch"
    # routing
    ROUTE_TARGET_MISMATCH = "route_target_mismatch"
    ROUTER_NOT_WIRED = "router_not_wired"
    PREDICATE_UNDEFINED = "predicate_undefined"
    MISSING_ELSE = "missing_else"
    # predicates
    PREDICATE_MISSING_IN_DOC = "predicate_missing_in_doc"
    PREDICATE_MISSING_IN_CODE = "predicate_missing_in_code"
    # data models / reducers
    MODEL_MISSING_IN_DOC = "model_missing_in_doc"
    MODEL_MISSING_IN_CODE = "model_missing_in_code"
    ATTR_MISSING_IN_DOC = "attr_missing_in_doc"
    ATTR_MISSING_IN_CODE = "attr_missing_in_code"
    ATTR_TYPE_DRIFT = "attr_type_drift"
    ATTR_REDUCER_DRIFT = "attr_reducer_drift"
    STATE_MODEL_MISMATCH = "state_model_mismatch"
    # metadata / prose
    META_DRIFT = "meta_drift"
    PROSE_DRIFT = "prose_drift"
    # carrier for a folded ir.Diagnostic with no dedicated category
    DIAGNOSTIC = "diagnostic"


# Folds a single-source ir.DiagnosticKind into a (category, severity). MISSING_ELSE
# and ROUTER_NOT_WIRED have dedicated categories; the rest ride the DIAGNOSTIC carrier.
DIAGNOSTIC_MAP: dict[DiagnosticKind, tuple[DriftCategory, Severity]] = {
    DiagnosticKind.MISSING_ELSE: (DriftCategory.MISSING_ELSE, Severity.ERROR),
    DiagnosticKind.ROUTER_NOT_WIRED: (DriftCategory.ROUTER_NOT_WIRED, Severity.ERROR),
    DiagnosticKind.IMPORT_FAILURE: (DriftCategory.DIAGNOSTIC, Severity.ERROR),
    DiagnosticKind.PARSE_ERROR: (DriftCategory.DIAGNOSTIC, Severity.ERROR),
    DiagnosticKind.COMMAND_WITHOUT_DESTINATIONS: (DriftCategory.DIAGNOSTIC, Severity.WARNING),
    DiagnosticKind.SEND_WITHOUT_DESTINATIONS: (DriftCategory.DIAGNOSTIC, Severity.WARNING),
    DiagnosticKind.NON_ENUMERABLE_TARGETS: (DriftCategory.DIAGNOSTIC, Severity.WARNING),
}

# Categories that are warnings by default; everything else defaults to ERROR.
_WARNING_DEFAULT = frozenset({DriftCategory.PROSE_DRIFT})


def default_severity(category: DriftCategory) -> Severity:
    return Severity.WARNING if category in _WARNING_DEFAULT else Severity.ERROR


HINTS: dict[DriftCategory, str] = {
    DriftCategory.NODE_MISSING_IN_DOC: "add the node to the diagram, or remove its @node",
    DriftCategory.NODE_MISSING_IN_CODE: "add an @node for the state, or drop it from the diagram",
    DriftCategory.ANNOTATION_NODE_MISMATCH: "an introspected node carries no @node; annotate it",
    DriftCategory.EDGE_MISSING_IN_DOC: "draw this transition in the diagram",
    DriftCategory.EDGE_MISSING_IN_CODE: "the diagram draws a transition the graph does not wire",
    DriftCategory.EDGE_CONDITIONALITY_MISMATCH: "conditional flag disagrees with the wiring",
    DriftCategory.EDGE_LABEL_MISMATCH: "the conditional label disagrees with the @predicate name",
    DriftCategory.ROUTE_TARGET_MISMATCH: "mapping and diagram aim a branch at different targets",
    DriftCategory.ROUTER_NOT_WIRED: "lg2m.router declared but no conditional edge wires it",
    DriftCategory.PREDICATE_UNDEFINED: "the route references a predicate with no @predicate",
    DriftCategory.MISSING_ELSE: "add the required (lg2m.ELSE, target) default branch",
    DriftCategory.PREDICATE_MISSING_IN_DOC: "document the predicate in the diagram/Predicates",
    DriftCategory.PREDICATE_MISSING_IN_CODE: "the doc names a predicate with no @predicate",
    DriftCategory.MODEL_MISSING_IN_DOC: "add a Data Models entry for the model",
    DriftCategory.MODEL_MISSING_IN_CODE: "the doc declares a model with no model decorator",
    DriftCategory.ATTR_MISSING_IN_DOC: "add the attribute row to the model table",
    DriftCategory.ATTR_MISSING_IN_CODE: "the table lists an attribute the schema lacks",
    DriftCategory.ATTR_TYPE_DRIFT: "the table type disagrees with the introspected schema",
    DriftCategory.ATTR_REDUCER_DRIFT: "the table reducer disagrees with the channel reducer",
    DriftCategory.STATE_MODEL_MISMATCH: "the @state_model and the documented graph state disagree",
    DriftCategory.META_DRIFT: "a metadata fact disagrees with introspection",
    DriftCategory.PROSE_DRIFT: "the documented prose and the code docstring differ (report-only)",
    DriftCategory.DIAGNOSTIC: "a single-source structural diagnostic was reported",
}
