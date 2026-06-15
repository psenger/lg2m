"""Assemble the two comparable ``GraphModel`` sides for ``reconcile`` (docs/design.md Section 8).

The parsers return ``MarkdownDoc`` / ``MermaidDiagram``; turning those into a
``GraphModel`` is the diff layer's job (the reader docstring says so). This module
owns that, plus the load-bearing ``canonicalize`` pass.

**Canonical form = topology vocabulary.** A real ``get_graph(xray=True)`` topology
has plain parallel edges (no ``<<fork>>`` / ``<<join>>`` pseudostates), flattened
``parent:child`` subgraph nodes (no composite state), and ``__start__`` / ``__end__``
sentinels (no ``[*]``). The introspector adapter produces that for free; it cannot
reconstruct the diagram's pseudostates/composites. So the *diagram* side absorbs the
transformation here, and the code side (already canonical) is only decorated with
annotation facts. ``canonicalize`` therefore runs on the doc side only.
"""

from __future__ import annotations

from dataclasses import dataclass

from lg2m.annotations.registry import Registry
from lg2m.ir import (
    Attribute,
    DataModel,
    Diagnostic,
    DiagnosticKind,
    Edge,
    GraphModel,
    Node,
    NodeKind,
    Predicate,
    Route,
    SourceLocation,
)
from lg2m.parsing import tables
from lg2m.parsing.markdown import MarkdownDoc
from lg2m.parsing.mermaid import START_END, MermaidDiagram, derive_routes, parse_mermaid
from lg2m.parsing.meta import parse_entity_meta

START_ID = "__start__"
END_ID = "__end__"

# Edges-table `kind` values that mean "the compiled graph reports this conditional".
# `command` is included: a Command(goto) declared via destinations is reported conditional
# by get_graph (verified against langgraph 1.2.5).
_CONDITIONAL_KINDS = frozenset({"conditional", "send", "command"})
# Edges-table `kind` values that mark a parallel fan-out/fan-in edge.
_PARALLEL_KINDS = frozenset({"fork", "parallel", "join"})


# --- doc-side assembly -------------------------------------------------------


def assemble_doc_model(doc: MarkdownDoc, *, file: str = "<md>") -> GraphModel:
    """Build a canonical doc-side ``GraphModel(origin="markdown")`` from a parsed doc.

    Connectivity comes from the mermaid block; the ``## Edges`` table ``kind`` column
    is the authority for per-edge classification (``send`` -> conditional, etc.).
    """
    diagram = parse_mermaid(doc.mermaid_lines, file=file)
    edge_kinds = _parse_edge_kinds(doc)
    nodes, edges, diagnostics = canonicalize(diagram, edge_kinds, file=file)

    gm = GraphModel(graph_id=doc.graph_id or "", origin="markdown")
    gm.nodes.update(nodes)
    gm.edges.extend(edges)
    gm.routes.update(derive_routes(diagram))  # logical names (e.g. else -> "investigate")
    gm.diagnostics.extend(diagram.diagnostics)
    gm.diagnostics.extend(diagnostics)

    graph_loc = _section_loc(doc, "Graph", file)
    for route in list(gm.routes.values()):
        gm.routes[route.source_id] = Route(
            source_id=route.source_id,
            branches=route.branches,
            else_target=route.else_target,
            loc=graph_loc,
        )

    for entity in doc.entities:
        loc = SourceLocation(file, entity.start + 1)
        if entity.section == "Predicates":
            gm.predicates[entity.id] = Predicate(name=entity.id, prose=entity.prose, loc=loc)
        elif entity.section == "Data Models":
            dm = _build_data_model(entity, loc)
            gm.models[dm.name] = dm
            if dm.is_graph_state:
                gm.state_model_name = dm.name
        gm.meta.extend(parse_entity_meta(entity.id, entity.lines))

    _attach_doc_node_locations(gm, doc, file)
    return gm


# --- code-side assembly ------------------------------------------------------


def assemble_code_model(
    topology: GraphModel,
    registry: Registry,
    locations: dict[tuple[str, str], SourceLocation],
) -> GraphModel:
    """Decorate the (already canonical) introspected topology with annotation facts.

    The topology is the authority on nodes/edges/state-schema; the registry adds
    which symbols are annotated and the declared router mapping; ``locations`` (from
    ``reader.merge_locations`` plus router locs keyed ``("router", source)``) supplies
    ``file:line``. A registry ``@node`` id matches a topology id exactly or by the
    ``<parent>:<id>`` subgraph-flattened form, so the flattened subgraph nodes are
    not false ``NODE_MISSING``.
    """
    gm = GraphModel(graph_id=topology.graph_id, origin="code")

    for nid, node in topology.nodes.items():
        anno_id = node.anno_id
        loc = node.loc
        if node.kind is NodeKind.NODE and anno_id is None:
            anno_id = _match_anno_node(nid, registry)
        docstring = node.docstring
        if anno_id is not None:
            loc = locations.get(("node", anno_id), loc)
            node_entry = registry.nodes.get(anno_id)
            if node_entry is not None and node_entry.docstring is not None:
                docstring = node_entry.docstring
        gm.nodes[nid] = Node(
            id=node.id, kind=node.kind, is_subgraph=node.is_subgraph, anno_id=anno_id,
            prose=node.prose, docstring=docstring, meta=node.meta, loc=loc,
        )

    gm.edges.extend(topology.edges)

    for source, entry in registry.routers.items():
        gm.routes[source] = Route(
            source_id=source,
            branches=entry.branches,
            else_target=entry.else_target,
            loc=locations.get(("router", source)),
        )

    for name, pred_entry in registry.predicates.items():
        gm.predicates[name] = Predicate(
            name=name, docstring=pred_entry.docstring, loc=locations.get(("predicate", name))
        )

    for name, dm in topology.models.items():
        kind = "state_model" if dm.is_graph_state else "data_model"
        gm.models[name] = DataModel(
            name=dm.name, style=dm.style, is_graph_state=dm.is_graph_state, anno=dm.anno,
            attributes=dm.attributes, prose=dm.prose,
            loc=locations.get((kind, name), dm.loc),
        )

    gm.state_model_name = topology.state_model_name or _state_model_from_registry(registry)
    gm.meta.extend(topology.meta)
    gm.diagnostics.extend(topology.diagnostics)
    return gm


def _match_anno_node(node_id: str, registry: Registry) -> str | None:
    if node_id in registry.nodes:
        return node_id
    return next((a for a in registry.nodes if node_id.endswith(f":{a}")), None)


def _state_model_from_registry(registry: Registry) -> str | None:
    return next((m.name for m in registry.models.values() if m.is_graph_state), None)


# --- canonicalization (diagram vocabulary -> topology vocabulary) ------------


@dataclass
class _WorkEdge:
    src: str
    dst: str
    predicate: str | None
    conditional: bool
    is_else: bool
    parallel: bool
    scope: str | None


def canonicalize(
    diagram: MermaidDiagram,
    edge_kinds: dict[tuple[str, str], str],
    *,
    file: str = "<md>",
) -> tuple[dict[str, Node], list[Edge], list[Diagnostic]]:
    """Rewrite a diagram into canonical topology vocabulary.

    Rule A collapses ``<<fork>>`` / ``<<join>>`` pseudostates into direct parallel
    edges; Rule B flattens a single-entry/single-exit composite into namespaced
    ``parent:child`` nodes and rewires its boundary; Rule C maps top-level ``[*]``
    to ``__start__`` / ``__end__``. Returns ``(nodes, edges, diagnostics)``.
    """
    states = diagram.states
    pseudo = {sid: s.pseudostate for sid, s in states.items() if s.pseudostate}
    composites = [sid for sid, s in states.items() if s.is_subgraph]
    diagnostics: list[Diagnostic] = []

    work: list[_WorkEdge] = []
    for e in diagram.edges:
        kind = edge_kinds.get((e.src, e.dst))
        conditional = e.conditional or kind in _CONDITIONAL_KINDS
        work.append(
            _WorkEdge(e.src, e.dst, e.predicate, conditional, e.is_else,
                      kind in _PARALLEL_KINDS, e.scope)
        )

    renamed: dict[str, str] = {}
    dropped: set[str] = set(pseudo)

    for comp in composites:
        interior = [w for w in work if w.scope == comp]
        entry, exit_ = _composite_entry_exit(interior)
        if entry is None or exit_ is None:
            diagnostics.append(
                Diagnostic(
                    DiagnosticKind.PARSE_ERROR,
                    comp,
                    f"composite {comp!r} is not single-entry/single-exit; cannot flatten",
                    SourceLocation(file, 0),
                )
            )
            continue
        for w in interior:
            for nid in (w.src, w.dst):
                if nid not in (START_END, comp):
                    renamed.setdefault(nid, f"{comp}:{nid}")
        work = _flatten_composite(work, comp, entry, exit_, renamed)
        dropped.add(comp)

    for pid in pseudo:
        work = _collapse_pseudostate(work, pid)

    for w in work:  # Rule C: top-level [*] -> sentinels
        if w.src == START_END:
            w.src = START_ID
        if w.dst == START_END:
            w.dst = END_ID

    nodes: dict[str, Node] = {
        START_ID: Node(id=START_ID, kind=NodeKind.START),
        END_ID: Node(id=END_ID, kind=NodeKind.END),
    }
    for sid in states:
        if sid in dropped:
            continue
        cid = renamed.get(sid, sid)
        nodes[cid] = Node(id=cid, kind=NodeKind.NODE)

    edges = [
        Edge(w.src, w.dst, w.predicate, conditional=w.conditional,
             is_else=w.is_else, parallel=w.parallel)
        for w in work
    ]
    return nodes, edges, diagnostics


def _composite_entry_exit(interior: list[_WorkEdge]) -> tuple[str | None, str | None]:
    entries = [w.dst for w in interior if w.src == START_END]
    exits = [w.src for w in interior if w.dst == START_END]
    if len(entries) == 1 and len(exits) == 1:
        return entries[0], exits[0]
    return None, None


def _flatten_composite(
    work: list[_WorkEdge], comp: str, entry: str, exit_: str, renamed: dict[str, str]
) -> list[_WorkEdge]:
    out: list[_WorkEdge] = []
    for w in work:
        if w.scope == comp:
            if w.src == START_END or w.dst == START_END:
                continue  # interior boundary marker
            out.append(
                _WorkEdge(renamed.get(w.src, w.src), renamed.get(w.dst, w.dst),
                          w.predicate, w.conditional, w.is_else, w.parallel, None)
            )
        else:
            src = f"{comp}:{exit_}" if w.src == comp else w.src
            dst = f"{comp}:{entry}" if w.dst == comp else w.dst
            out.append(
                _WorkEdge(src, dst, w.predicate, w.conditional, w.is_else, w.parallel, w.scope)
            )
    return out


def _collapse_pseudostate(work: list[_WorkEdge], pid: str) -> list[_WorkEdge]:
    ins = [w for w in work if w.dst == pid]
    outs = [w for w in work if w.src == pid]
    spliced = [
        _WorkEdge(a.src, b.dst, None, False, False, True, None) for a in ins for b in outs
    ]
    kept = [w for w in work if w.src != pid and w.dst != pid]
    return kept + spliced


# --- doc helpers -------------------------------------------------------------


def _parse_edge_kinds(doc: MarkdownDoc) -> dict[tuple[str, str], str]:
    section = doc.sections.get("Edges")
    if section is None:
        return {}
    parsed = tables.parse_table(section.lines)
    if parsed is None:
        return {}
    _, rows = parsed
    kinds: dict[tuple[str, str], str] = {}
    for r in rows:
        src, dst, kind = _strip_bt(r.get("from", "")), _strip_bt(r.get("to", "")), r.get("kind", "")
        if src and dst:
            kinds[(src, dst)] = kind.strip()
    return kinds


def _build_data_model(entity, loc: SourceLocation) -> DataModel:
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
            if "attribute" in r
        )
    return DataModel(
        name=entity.id,
        style="",  # code-side fact (TypedDict/BaseModel); the doc cannot know it
        is_graph_state="@state_model" in entity.prose,
        attributes=attributes,
        prose=entity.prose,
        loc=loc,
    )


def _attach_doc_node_locations(gm: GraphModel, doc: MarkdownDoc, file: str) -> None:
    """Point each canonical node at its ``### `` heading in the Nodes section."""
    for entity in doc.entities:
        if entity.section != "Nodes":
            continue
        cid = _canonical_node_id(gm, entity.id)
        if cid is None:
            continue
        node = gm.nodes[cid]
        gm.nodes[cid] = Node(
            id=node.id, kind=node.kind, is_subgraph=node.is_subgraph, anno_id=node.anno_id,
            prose=node.prose, docstring=node.docstring, meta=node.meta,
            loc=SourceLocation(file, entity.start + 1),
        )


def _canonical_node_id(gm: GraphModel, logical_id: str) -> str | None:
    if logical_id in gm.nodes:
        return logical_id
    suffix = f":{logical_id}"
    return next((nid for nid in gm.nodes if nid.endswith(suffix)), None)


def _section_loc(doc: MarkdownDoc, name: str, file: str) -> SourceLocation | None:
    section = doc.sections.get(name)
    return SourceLocation(file, section.start + 1) if section is not None else None


def _strip_bt(text: str) -> str:
    return text.strip().strip("`").strip()
