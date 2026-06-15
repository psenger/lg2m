"""Reconcile two assembled GraphModels into a DriftReport (docs/design.md Section 8).

``reconcile`` is a pure function of two already-assembled, already-canonical
``GraphModel``s — the code side (topology + annotations) and the doc side (the
Markdown contract). It does not parse, introspect, or canonicalize; that is the
assembler's job. Each per-category check is set/dict arithmetic over the IR's
structural identity (``Edge`` identity is ``(src, dst, predicate)``), so the clean
oracle — where all three upstream sources agree — yields an empty report.
"""

from __future__ import annotations

from collections.abc import Callable

from lg2m.diff.categories import (
    DIAGNOSTIC_MAP,
    HINTS,
    DriftCategory,
    Severity,
    default_severity,
)
from lg2m.ir import GraphModel, MetaKind, NodeKind, SourceLocation
from lg2m.report.model import DriftItem, DriftReport
from lg2m.sync.normalize import prose_equal


def reconcile(code: GraphModel, doc: GraphModel, *, strict: bool = False) -> DriftReport:
    """Compare a canonical code-side model against a canonical doc-side model.

    ``strict`` escalates WARNING diagnostics (e.g. non-enumerable targets) to ERROR.
    """
    report = DriftReport(graph_id=code.graph_id or doc.graph_id)
    for check in _CHECKS:
        check(code, doc, report)
    _fold_diagnostics(code, report, strict=strict)
    _fold_diagnostics(doc, report, strict=strict)
    return report


def diagnostics_report(graph_id: str, gm: GraphModel, *, strict: bool = False) -> DriftReport:
    """A DriftReport of only ``gm``'s folded diagnostics (used when loading the graph fails)."""
    report = DriftReport(graph_id=graph_id)
    _fold_diagnostics(gm, report, strict=strict)
    return report


def _item(
    category: DriftCategory,
    subject: str,
    message: str,
    *,
    code_loc: SourceLocation | None = None,
    doc_loc: SourceLocation | None = None,
    severity: Severity | None = None,
) -> DriftItem:
    return DriftItem(
        category=category,
        severity=severity or default_severity(category),
        subject=subject,
        message=message,
        code_loc=code_loc,
        doc_loc=doc_loc,
        hint=HINTS.get(category),
    )


# --- nodes -------------------------------------------------------------------


def _check_nodes(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    for nid in code.nodes.keys() - doc.nodes.keys():
        report.add(_item(DriftCategory.NODE_MISSING_IN_DOC, nid,
                         f"node {nid!r} is in code but not the diagram",
                         code_loc=code.nodes[nid].loc))
    for nid in doc.nodes.keys() - code.nodes.keys():
        report.add(_item(DriftCategory.NODE_MISSING_IN_CODE, nid,
                         f"node {nid!r} is in the diagram but not code",
                         doc_loc=doc.nodes[nid].loc))
    for nid, node in code.nodes.items():
        if node.kind is NodeKind.NODE and node.anno_id is None:
            report.add(_item(DriftCategory.ANNOTATION_NODE_MISMATCH, nid,
                             f"introspected node {nid!r} carries no @node",
                             code_loc=node.loc))


# --- edges -------------------------------------------------------------------


def _edge_label(key: tuple[str, str, str | None]) -> str:
    src, dst, predicate = key
    return f"{src} -> {dst}" + (f": {predicate}" if predicate else "")


def _check_edges(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    code_by_id = {(e.src_id, e.dst_id, e.predicate): e for e in code.edges}
    doc_by_id = {(e.src_id, e.dst_id, e.predicate): e for e in doc.edges}
    code_only = set(code_by_id) - set(doc_by_id)
    doc_only = set(doc_by_id) - set(code_by_id)

    # Same (src, dst) with a different predicate is a label mismatch, not two misses.
    for c in list(code_only):
        match = next((d for d in doc_only if d[0] == c[0] and d[1] == c[1] and d[2] != c[2]), None)
        if match is not None:
            code_only.discard(c)
            doc_only.discard(match)
            report.add(_item(DriftCategory.EDGE_LABEL_MISMATCH, f"{c[0]} -> {c[1]}",
                             f"label differs: code {c[2]!r} vs diagram {match[2]!r}",
                             code_loc=code_by_id[c].loc, doc_loc=doc_by_id[match].loc))

    for c in code_only:
        report.add(_item(DriftCategory.EDGE_MISSING_IN_DOC, _edge_label(c),
                         "transition in code but not the diagram", code_loc=code_by_id[c].loc))
    for d in doc_only:
        report.add(_item(DriftCategory.EDGE_MISSING_IN_CODE, _edge_label(d),
                         "transition in the diagram but not code", doc_loc=doc_by_id[d].loc))

    for key in code_by_id.keys() & doc_by_id.keys():
        if code_by_id[key].conditional != doc_by_id[key].conditional:
            report.add(_item(DriftCategory.EDGE_CONDITIONALITY_MISMATCH, _edge_label(key),
                             f"conditional code={code_by_id[key].conditional} "
                             f"doc={doc_by_id[key].conditional}",
                             code_loc=code_by_id[key].loc, doc_loc=doc_by_id[key].loc))


# --- routing -----------------------------------------------------------------


def _fmt_route(route) -> str:
    return f"branches={list(route.branches)} else={route.else_target!r}"


def _check_routes(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    wired = {e.src_id for e in code.edges if e.conditional}
    for source in code.routes.keys() | doc.routes.keys():
        c = code.routes.get(source)
        d = doc.routes.get(source)
        cloc = c.loc if c is not None else None
        dloc = d.loc if d is not None else None

        if c is not None:
            for pred, _target in c.branches:
                if pred not in code.predicates:
                    report.add(_item(DriftCategory.PREDICATE_UNDEFINED, f"{source}:{pred}",
                                     f"route {source!r} references undefined predicate {pred!r}",
                                     code_loc=cloc))
            if source not in wired:
                msg = f"lg2m.router({source!r}) declared but no conditional edge wires it"
                report.add(_item(DriftCategory.ROUTER_NOT_WIRED, source, msg, code_loc=cloc))

        if c is not None and not c.else_target:
            report.add(_item(DriftCategory.MISSING_ELSE, source,
                             f"router {source!r} has no [else] default", code_loc=cloc))
        if d is not None and not d.else_target:
            report.add(_item(DriftCategory.MISSING_ELSE, source,
                             f"fan-out at {source!r} has no [else] in the diagram", doc_loc=dloc))

        if c is not None and d is not None:
            if c.branches != d.branches or c.else_target != d.else_target:
                report.add(_item(DriftCategory.ROUTE_TARGET_MISMATCH, source,
                                 f"mapping {_fmt_route(c)} != diagram {_fmt_route(d)}",
                                 code_loc=cloc, doc_loc=dloc))
        elif d is not None:  # diagram routes here but no lg2m.router declared
            report.add(_item(DriftCategory.ROUTER_NOT_WIRED, source,
                             f"diagram routes from {source!r} but no lg2m.router is declared",
                             doc_loc=dloc))
        else:  # declared but the diagram draws no conditional branch
            report.add(_item(DriftCategory.ROUTE_TARGET_MISMATCH, source,
                             f"lg2m.router({source!r}) declared but the diagram draws no branch",
                             code_loc=cloc))


# --- predicates --------------------------------------------------------------


def _check_predicates(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    for name in code.predicates.keys() - doc.predicates.keys():
        report.add(_item(DriftCategory.PREDICATE_MISSING_IN_DOC, name,
                         f"predicate {name!r} is annotated but not documented",
                         code_loc=code.predicates[name].loc))
    for name in doc.predicates.keys() - code.predicates.keys():
        report.add(_item(DriftCategory.PREDICATE_MISSING_IN_CODE, name,
                         f"predicate {name!r} is documented but has no @predicate",
                         doc_loc=doc.predicates[name].loc))


# --- data models / reducers --------------------------------------------------


def _check_models(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    for name in code.models.keys() - doc.models.keys():
        report.add(_item(DriftCategory.MODEL_MISSING_IN_DOC, name,
                         f"model {name!r} is annotated but not documented",
                         code_loc=code.models[name].loc))
    for name in doc.models.keys() - code.models.keys():
        report.add(_item(DriftCategory.MODEL_MISSING_IN_CODE, name,
                         f"model {name!r} is documented but has no decorator",
                         doc_loc=doc.models[name].loc))

    if code.state_model_name != doc.state_model_name:
        report.add(_item(DriftCategory.STATE_MODEL_MISMATCH, code.state_model_name or "?",
                         f"graph state is {code.state_model_name!r} in code, "
                         f"{doc.state_model_name!r} in the doc"))

    for name in code.models.keys() & doc.models.keys():
        _check_attributes(code.models[name], doc.models[name], report)


def _check_attributes(code_model, doc_model, report: DriftReport) -> None:
    code_attrs = {a.name: a for a in code_model.attributes}
    doc_attrs = {a.name: a for a in doc_model.attributes}
    for attr in code_attrs.keys() - doc_attrs.keys():
        report.add(_item(DriftCategory.ATTR_MISSING_IN_DOC, f"{code_model.name}.{attr}",
                         f"attribute {attr!r} of {code_model.name!r} is not documented",
                         code_loc=code_model.loc))
    for attr in doc_attrs.keys() - code_attrs.keys():
        report.add(_item(DriftCategory.ATTR_MISSING_IN_CODE, f"{doc_model.name}.{attr}",
                         f"attribute {attr!r} of {doc_model.name!r} is not in the schema",
                         doc_loc=doc_model.loc))
    for attr in code_attrs.keys() & doc_attrs.keys():
        c, d = code_attrs[attr], doc_attrs[attr]
        subject = f"{code_model.name}.{attr}"
        if c.type_str != d.type_str:
            report.add(_item(DriftCategory.ATTR_TYPE_DRIFT, subject,
                             f"type {c.type_str!r} (code) != {d.type_str!r} (doc)",
                             code_loc=code_model.loc, doc_loc=doc_model.loc))
        if c.reducer != d.reducer:
            report.add(_item(DriftCategory.ATTR_REDUCER_DRIFT, subject,
                             f"reducer {c.reducer!r} (code) != {d.reducer!r} (doc)",
                             code_loc=code_model.loc, doc_loc=doc_model.loc))


# --- metadata ----------------------------------------------------------------


def _clean(text: str) -> str:
    return text.strip().strip("`").strip()


def _clean_list(text: str) -> list[str]:
    return [item for item in (_clean(p) for p in text.split(",")) if item]


def _check_meta(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    """Confirm each documented metadata fact against introspection where derivable.

    Only the keys with an introspectable counterpart are checked; informational keys
    (``width``, ``merges``) and free-text ``> Note:`` blocks are carried, never drift.
    """
    state = code.models.get(code.state_model_name) if code.state_model_name else None
    reducers = {a.name: a.reducer for a in state.attributes} if state is not None else {}
    out_targets: dict[str, set[str]] = {}
    for edge in code.edges:
        out_targets.setdefault(edge.src_id, set()).add(edge.dst_id)

    for meta in doc.meta:
        if meta.kind is MetaKind.NOTE or not isinstance(meta.data, dict):
            continue
        data, owner, mloc = meta.data, meta.owner_id, meta.loc
        targets = out_targets.get(owner, set())

        if "reducer" in data and "channel" in data:
            channel, declared = _clean(data["channel"]), _clean(data["reducer"])
            if reducers.get(channel) != declared:
                report.add(_item(DriftCategory.META_DRIFT, owner,
                                 f"{owner}: reducer {declared!r} on {channel!r} != "
                                 f"schema {reducers.get(channel)!r}", doc_loc=mloc))

        for key in ("command_goto", "send_worker"):
            if key in data:
                target = _clean(data[key])
                if target not in targets:
                    report.add(_item(DriftCategory.META_DRIFT, owner,
                                     f"{owner}: declared {key}={target!r} but no such edge",
                                     doc_loc=mloc))

        if "targets" in data:
            declared_targets = set(_clean_list(data["targets"]))
            if not declared_targets <= targets:
                report.add(_item(DriftCategory.META_DRIFT, owner,
                                 f"{owner}: declared targets {sorted(declared_targets)} "
                                 f"not all wired {sorted(targets)}", doc_loc=mloc))


# --- prose -------------------------------------------------------------------


def _check_prose(code: GraphModel, doc: GraphModel, report: DriftReport) -> None:
    """Report-only (WARNING): compare only when BOTH sides carry prose (docs/design.md Section 12).

    Covers nodes and predicates; both carry a code-side ``docstring`` and a doc-side
    ``prose``. Equality is on the normalized form so docstring body-indentation and
    Markdown column-0 prose do not register as drift.
    """
    for nid in code.nodes.keys() & doc.nodes.keys():
        c_doc, d_prose = code.nodes[nid].docstring, doc.nodes[nid].prose
        if c_doc and d_prose and not prose_equal(c_doc, d_prose):
            report.add(_item(DriftCategory.PROSE_DRIFT, nid,
                             f"prose for {nid!r} differs between code docstring and doc",
                             code_loc=code.nodes[nid].loc, doc_loc=doc.nodes[nid].loc))
    for name in code.predicates.keys() & doc.predicates.keys():
        c_doc, d_prose = code.predicates[name].docstring, doc.predicates[name].prose
        if c_doc and d_prose and not prose_equal(c_doc, d_prose):
            report.add(_item(DriftCategory.PROSE_DRIFT, name,
                             f"prose for {name!r} differs between code docstring and doc",
                             code_loc=code.predicates[name].loc, doc_loc=doc.predicates[name].loc))


# --- diagnostics fold --------------------------------------------------------


def _fold_diagnostics(gm: GraphModel, report: DriftReport, *, strict: bool) -> None:
    fallback = (DriftCategory.DIAGNOSTIC, Severity.WARNING)
    for diag in gm.diagnostics:
        category, severity = DIAGNOSTIC_MAP.get(diag.kind, fallback)
        if strict and severity is Severity.WARNING:
            severity = Severity.ERROR
        report.add(DriftItem(
            category=category,
            severity=severity,
            subject=diag.subject,
            message=diag.message,
            code_loc=diag.loc if gm.origin == "code" else None,
            doc_loc=diag.loc if gm.origin == "markdown" else None,
            hint=HINTS.get(category),
        ))


_CHECKS: tuple[Callable[[GraphModel, GraphModel, DriftReport], None], ...] = (
    _check_nodes,
    _check_edges,
    _check_routes,
    _check_predicates,
    _check_models,
    _check_meta,
    _check_prose,
)
