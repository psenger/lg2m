"""The ``check`` orchestration: reconcile a configured graph against its Markdown contract.

Wires the layers end-to-end — config -> resolve -> load (run user code) -> introspect (the real
topology) -> read annotations -> assemble both sides -> reconcile -> ``DriftReport``. The framework
adapter is imported **lazily**, so ``import lg2m.pipeline`` pulls in no framework; only calling
``check()`` (which runs user code that imports the framework anyway) reaches it.

Annotation discovery uses the AST reader over the package's source files, not the live import
chain: the Model-A router resolves predicate names lazily and never imports the predicates module,
so a predicate can be annotated yet not "live". The reader sees every annotation in source.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
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
from lg2m.config import loader as config_loader
from lg2m.diff.assemble import assemble_code_model, assemble_doc_model
from lg2m.diff.categories import HINTS, DriftCategory, Severity, default_severity
from lg2m.diff.engine import diagnostics_report, reconcile
from lg2m.discovery.resolve import resolve
from lg2m.introspect.loader import load_compiled
from lg2m.ir import Diagnostic, GraphModel, SourceLocation
from lg2m.parsing.markdown import parse_markdown
from lg2m.report.model import DriftItem, DriftReport


def check(config_path: str | Path, graph_id: str, *, strict: bool = False) -> DriftReport:
    """Reconcile the configured ``graph_id`` against its Markdown contract."""
    config_path = Path(config_path)
    graphs = config_loader.load(config_path)
    if graph_id not in graphs:
        return _usage_report(graph_id, f"no graph {graph_id!r} in {config_path}")

    resolved = resolve(graphs[graph_id], base_dir=config_path.parent, graph_id=graph_id)
    doc = assemble_doc_model(
        parse_markdown(resolved.markdown_path.read_text(encoding="utf-8"),
                       file=str(resolved.markdown_path)),
        file=str(resolved.markdown_path),
    )

    loaded = load_compiled(resolved)
    if loaded.compiled is None:
        gm = GraphModel(graph_id=graph_id, origin="code", diagnostics=loaded.diagnostics)
        report = diagnostics_report(graph_id, gm, strict=strict)
        report.items.extend(diagnostics_report(graph_id, doc, strict=strict).items)
        return report

    from lg2m.introspect.langgraph_adapter import LangGraphIntrospector  # lazy: framework import

    introspector = LangGraphIntrospector(
        loaded.compiled, xray=resolved.xray, registry=get_registry()
    )
    topology = introspector.introspect(graph_id)

    package_dir = Path(sys.modules[resolved.module].__file__).parent
    registry, locations = gather_annotations(package_dir)
    code = assemble_code_model(topology, registry, locations)
    return reconcile(code, doc, strict=strict)


def validate(config_path: str | Path, graph_id: str, *, strict: bool = False) -> DriftReport:
    """Light pre-flight for a configured graph: cheaper than ``check``, no full reconcile.

    Confirms each side parses, the entry point imports, exactly one ``@state_model`` exists, and
    every conditional fan-out in the diagram has an ``[else]`` default. It never reconciles and
    never imports the framework adapter. A code-side router missing its ``[else]`` cannot reach the
    annotation checks: ``lg2m.router`` rejects that at construction, so such a module fails to
    import and surfaces as ``IMPORT_FAILURE`` instead.
    """
    config_path = Path(config_path)
    graphs = config_loader.load(config_path)
    if graph_id not in graphs:
        return _usage_report(graph_id, f"no graph {graph_id!r} in {config_path}")

    resolved = resolve(graphs[graph_id], base_dir=config_path.parent, graph_id=graph_id)
    report = DriftReport(graph_id=graph_id)

    md_file = str(resolved.markdown_path)
    try:
        text = resolved.markdown_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.add(_drift(DriftCategory.DIAGNOSTIC, graph_id,
                          f"cannot read markdown {md_file}: {exc!r}",
                          doc_loc=SourceLocation(md_file, 0)))
    else:
        doc = assemble_doc_model(parse_markdown(text, file=md_file), file=md_file)
        report.items.extend(diagnostics_report(graph_id, doc, strict=strict).items)
        for route in doc.routes.values():
            if not route.else_target:
                report.add(_drift(DriftCategory.MISSING_ELSE, route.source_id,
                                  f"fan-out at {route.source_id!r} has no [else] in the diagram",
                                  doc_loc=route.loc))

    loaded = load_compiled(resolved)
    if loaded.compiled is None:
        gm = GraphModel(graph_id=graph_id, origin="code", diagnostics=loaded.diagnostics)
        report.items.extend(diagnostics_report(graph_id, gm, strict=strict).items)
        return report

    package_dir = Path(sys.modules[resolved.module].__file__).parent
    registry, _locations = gather_annotations(package_dir)
    state_models = [m for m in registry.models.values() if m.is_graph_state]
    if len(state_models) != 1:
        report.add(_drift(DriftCategory.STATE_MODEL_MISMATCH, graph_id,
                          f"expected exactly one @state_model, found {len(state_models)}"))
    return report


@dataclass
class CodeModelResult:
    """The assembled code-side model for ``gen --from-code``, or ``None`` on a load failure."""

    model: GraphModel | None
    diagnostics: list[Diagnostic] = field(default_factory=list)


def build_code_model(config_path: str | Path, graph_id: str) -> CodeModelResult:
    """Load + introspect ``graph_id`` and assemble its code-side ``GraphModel``.

    The same chain ``check`` runs, minus the doc side and the reconcile. Returns
    ``CodeModelResult(None, diagnostics)`` when the user graph cannot be imported/compiled. The
    framework adapter is imported lazily, so this stays import-light until the graph actually loads.
    """
    config_path = Path(config_path)
    graphs = config_loader.load(config_path)
    resolved = resolve(graphs[graph_id], base_dir=config_path.parent, graph_id=graph_id)

    loaded = load_compiled(resolved)
    if loaded.compiled is None:
        return CodeModelResult(None, loaded.diagnostics)

    from lg2m.introspect.langgraph_adapter import LangGraphIntrospector  # lazy: framework import

    introspector = LangGraphIntrospector(
        loaded.compiled, xray=resolved.xray, registry=get_registry()
    )
    topology = introspector.introspect(graph_id)

    package_dir = Path(sys.modules[resolved.module].__file__).parent
    registry, locations = gather_annotations(package_dir)
    return CodeModelResult(assemble_code_model(topology, registry, locations))


def _drift(
    category: DriftCategory,
    subject: str,
    message: str,
    *,
    code_loc: SourceLocation | None = None,
    doc_loc: SourceLocation | None = None,
) -> DriftItem:
    return DriftItem(
        category=category,
        severity=default_severity(category),
        subject=subject,
        message=message,
        code_loc=code_loc,
        doc_loc=doc_loc,
        hint=HINTS.get(category),
    )


def gather_annotations(
    package_dir: Path,
) -> tuple[Registry, dict[tuple[str, str], SourceLocation]]:
    """Recover the full annotation set from a package's source via the AST reader.

    Reads every ``*.py`` in the package directory (no import), so it sees annotations the live
    import chain misses. Returns a fresh ``Registry`` plus a ``(kind, key) -> SourceLocation`` map
    that also carries ``("router", source)`` keys, the shape ``assemble_code_model`` consumes.
    """
    registry = Registry()
    locations: dict[tuple[str, str], SourceLocation] = {}
    for path in sorted(package_dir.glob("*.py")):
        result = reader.read_file(path)
        for ref in result.annotations:
            if ref.kind == "node":
                registry.nodes[ref.key] = NodeEntry(
                    ref.key, _stub, None, ref.loc.line, ref.docstring
                )
            elif ref.kind == "predicate":
                registry.predicates[ref.key] = PredicateEntry(
                    ref.key, _stub, None, ref.loc.line, ref.docstring
                )
            elif ref.kind in ("state_model", "data_model"):
                registry.models[ref.key] = ModelEntry(
                    ref.key, object, ref.kind == "state_model", None, ref.loc.line
                )
        for route in result.routers:
            registry.routers[route.source_id] = RouterEntry(
                route.source_id, route.branches, route.else_target or "", _stub, None,
                route.loc.line,
            )
            locations[("router", route.source_id)] = route.loc
        locations.update(reader.merge_locations(result, registry))
    return registry, locations


def _stub(*_args, **_kwargs):  # registry targets the diff never calls
    return None


def _usage_report(graph_id: str, message: str) -> DriftReport:
    report = DriftReport(graph_id=graph_id)
    report.add(DriftItem(DriftCategory.DIAGNOSTIC, Severity.ERROR, graph_id, message))
    return report
