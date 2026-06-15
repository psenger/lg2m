"""Mermaid ``stateDiagram-v2`` parser and emitter (docs/design.md Section 7).

lg2m owns this parser/emitter; no third-party mermaid library is used. The parser
is a line classifier with a composite-state stack. Line kinds, classified in this
order (the order matters — a composite-open and a pseudostate decl both start with
``state ``):

1. composite close ``}``
2. composite open ``state <id> {``  -> push scope, mark the state a subgraph
3. pseudostate decl ``state <id> <<fork>>`` / ``<<join>>``
4. transition ``a --> b`` / ``a --> b: predicate`` / ``a --> c: [else]``

``[*]`` is never a named state; it is kept literally on the edge endpoint, and its
START/END sense is read from its position (left = start, right = end) within the
current composite scope. Emit walks edges in parse order, opening/closing the
composite block as the scope changes, so ``parse(emit(parse(x)))`` preserves the
edge order and the nesting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lg2m.ir import ELSE_LABEL, Diagnostic, DiagnosticKind, Route

START_END = "[*]"

_COMPOSITE_OPEN = re.compile(r"^state\s+(\S+)\s*\{$")
_PSEUDO = re.compile(r"^state\s+(\S+)\s+<<(fork|join)>>$")
_TRANSITION = re.compile(r"^(.+?)\s*-->\s*([^:]+?)\s*(?::\s*(.+?))?\s*$")


@dataclass
class MermaidState:
    id: str
    is_subgraph: bool = False
    pseudostate: str | None = None  # "fork" | "join" | None
    parent: str | None = None  # composite owner id, or None at top level


@dataclass
class MermaidEdge:
    src: str
    dst: str
    predicate: str | None = None
    conditional: bool = False
    is_else: bool = False
    scope: str | None = None  # composite owner id, or None at top level


@dataclass
class MermaidDiagram:
    states: dict[str, MermaidState] = field(default_factory=dict)
    edges: list[MermaidEdge] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def named_state_ids(self) -> list[str]:
        """State ids declared in the diagram (``[*]`` is never one)."""
        return list(self.states)


def parse_mermaid(lines: list[str], *, file: str = "<mermaid>") -> MermaidDiagram:
    diagram = MermaidDiagram()
    scope: list[str] = []

    for lineno, raw in enumerate(lines, start=1):
        s = raw.strip()
        if not s or s.startswith("%%") or s == "stateDiagram-v2":
            continue

        if s == "}":
            if scope:
                scope.pop()
            else:
                _parse_error(diagram, file, lineno, "unbalanced '}'")
            continue

        m = _COMPOSITE_OPEN.match(s)
        if m:
            state = _ensure_state(diagram, m.group(1), scope)
            state.is_subgraph = True
            scope.append(m.group(1))
            continue

        m = _PSEUDO.match(s)
        if m:
            _ensure_state(diagram, m.group(1), scope).pseudostate = m.group(2)
            continue

        m = _TRANSITION.match(s)
        if m:
            _add_transition(diagram, m.group(1).strip(), m.group(2).strip(), m.group(3), scope)
            continue

        _parse_error(diagram, file, lineno, f"unrecognized line: {s!r}")

    if scope:
        _parse_error(diagram, file, len(lines), f"unclosed composite state(s): {scope}")
    return diagram


def emit_mermaid(diagram: MermaidDiagram) -> list[str]:
    out = ["stateDiagram-v2"]
    for state in diagram.states.values():
        if state.pseudostate is not None:
            out.append(f"state {state.id} <<{state.pseudostate}>>")

    current: str | None = None
    for edge in diagram.edges:
        if edge.scope != current:
            if current is not None:
                out.append("}")
            if edge.scope is not None:
                out.append(f"state {edge.scope} {{")
            current = edge.scope
        indent = "    " if edge.scope is not None else ""
        out.append(indent + _format_edge(edge))
    if current is not None:
        out.append("}")
    return out


def derive_routes(diagram: MermaidDiagram) -> dict[str, Route]:
    """Group the conditional edges of each source into a ``Route`` (ordered)."""
    by_src: dict[str, list[MermaidEdge]] = {}
    for edge in diagram.edges:
        if edge.conditional:
            by_src.setdefault(edge.src, []).append(edge)

    routes: dict[str, Route] = {}
    for src, edges in by_src.items():
        branches = tuple((e.predicate, e.dst) for e in edges if not e.is_else)
        else_edge = next((e for e in edges if e.is_else), None)
        routes[src] = Route(
            source_id=src,
            branches=branches,
            else_target=else_edge.dst if else_edge is not None else None,
        )
    return routes


def _ensure_state(diagram: MermaidDiagram, state_id: str, scope: list[str]) -> MermaidState:
    state = diagram.states.get(state_id)
    if state is None:
        state = MermaidState(id=state_id, parent=scope[-1] if scope else None)
        diagram.states[state_id] = state
    return state


def _add_transition(
    diagram: MermaidDiagram, src: str, dst: str, label: str | None, scope: list[str]
) -> None:
    if src != START_END:
        _ensure_state(diagram, src, scope)
    if dst != START_END:
        _ensure_state(diagram, dst, scope)

    predicate: str | None = None
    conditional = False
    is_else = False
    if label is not None:
        label = label.strip()
        conditional = True
        if label == ELSE_LABEL:
            is_else = True
            predicate = ELSE_LABEL
        else:
            predicate = label

    diagram.edges.append(
        MermaidEdge(
            src=src,
            dst=dst,
            predicate=predicate,
            conditional=conditional,
            is_else=is_else,
            scope=scope[-1] if scope else None,
        )
    )


def _format_edge(edge: MermaidEdge) -> str:
    if edge.predicate is not None:
        return f"{edge.src} --> {edge.dst}: {edge.predicate}"
    return f"{edge.src} --> {edge.dst}"


def _parse_error(diagram: MermaidDiagram, file: str, line: int, message: str) -> None:
    diagram.diagnostics.append(
        Diagnostic(
            kind=DiagnosticKind.PARSE_ERROR,
            subject=file,
            message=f"{file}:{line}: {message}",
        )
    )
