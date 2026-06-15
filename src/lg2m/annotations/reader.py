"""AST recovery of lg2m annotations from a source file read as text.

The file is parsed with ``ast`` and never imported, so reading an annotated module
that imports langgraph does NOT import langgraph (this layer is framework-free).
The reader recovers, with file:line:

  @node("id") / @predicate("name")            -> AnnoRef(kind, key, loc)
  @state_model / @data_model (bare)           -> AnnoRef(kind, class_name, loc)
  lg2m.router("src", [(pred, tgt), (ELSE, t)]) -> ir.Route(source_id, branches,
                                                  else_target, loc)

ELSE is recovered whether written ``lg2m.ELSE`` (ast.Attribute) or imported as a
bare ``ELSE`` (ast.Name). Recovery is literal and total: an element given as a
non-literal expression is skipped, never guessed and never raised on.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from lg2m.annotations.registry import Registry
from lg2m.ir import Route, SourceLocation


@dataclass(frozen=True)
class AnnoRef:
    kind: str  # "node" | "predicate" | "state_model" | "data_model"
    key: str  # the id, the predicate name, or the class __name__
    loc: SourceLocation
    # Populated for "node"/"predicate" only (sync reconciles their docstrings).
    docstring: str | None = None  # ast.get_docstring text; None when absent
    doc_span: tuple[int, int] | None = None  # (start_lineno, end_lineno), 1-based inclusive
    body_col: int | None = None  # col_offset of body[0]; the docstring insertion indent
    body_lineno: int | None = None  # lineno of body[0], 1-based; the insertion anchor


@dataclass(frozen=True)
class ReaderResult:
    annotations: tuple[AnnoRef, ...]
    routers: tuple[Route, ...]


def read_file(path: str | Path) -> ReaderResult:
    path = str(path)
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)

    annos: list[AnnoRef] = []
    routers: list[Route] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            annos.extend(_decorators_on(node, path))
        elif isinstance(node, ast.Call) and _is_router_call(node):
            route = _router_route(node, path)
            if route is not None:
                routers.append(route)

    return ReaderResult(tuple(annos), tuple(routers))


def merge_locations(
    result: ReaderResult, registry: Registry
) -> dict[tuple[str, str], SourceLocation]:
    """Map (kind, key) -> SourceLocation for each annotation also in the registry.

    The runtime registry is the authority on "this object exists and is live"; the
    reader is the authority on file:line. This keyed view is what the later
    assembly attaches to the IR Node/Predicate/DataModel.
    """
    out: dict[tuple[str, str], SourceLocation] = {}
    for ref in result.annotations:
        if _in_registry(ref, registry):
            out[(ref.kind, ref.key)] = ref.loc
    return out


def _in_registry(ref: AnnoRef, registry: Registry) -> bool:
    if ref.kind == "node":
        return ref.key in registry.nodes
    if ref.kind == "predicate":
        return ref.key in registry.predicates
    if ref.kind in ("state_model", "data_model"):
        return ref.key in registry.models
    return False


def _decorators_on(node: ast.AST, path: str) -> list[AnnoRef]:
    refs: list[AnnoRef] = []
    docstring, doc_span, body_col, body_lineno = _doc_fields(node)
    for dec in node.decorator_list:  # type: ignore[attr-defined]
        kind, key = _classify_decorator(dec, node)
        if kind is None or key is None:
            continue
        loc = SourceLocation(path, dec.lineno)
        if kind in ("node", "predicate"):
            refs.append(AnnoRef(kind, key, loc, docstring, doc_span, body_col, body_lineno))
        else:
            refs.append(AnnoRef(kind, key, loc))
    return refs


def _doc_fields(
    node: ast.AST,
) -> tuple[str | None, tuple[int, int] | None, int | None, int | None]:
    """Recover (docstring, (start,end), body_col, body_lineno) from a def/class via ``ast``.

    ``body_col``/``body_lineno`` locate the first body statement (the insertion point and
    indent when there is no docstring); ``doc_span`` is None when the first statement is
    not a string literal.
    """
    body = getattr(node, "body", None)
    if not body:
        return None, None, None, None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value.value, (first.lineno, first.end_lineno), first.col_offset, first.lineno
    return None, None, first.col_offset, first.lineno


def _classify_decorator(dec: ast.expr, node: ast.AST) -> tuple[str | None, str | None]:
    if isinstance(dec, ast.Call):  # @node("id") / @predicate("name")
        name = _callee_name(dec.func)
        if name in ("node", "predicate"):
            return name, (_str_const(dec.args[0]) if dec.args else None)
        return None, None

    name = _callee_name(dec)  # bare @state_model / @data_model
    if name in ("state_model", "data_model"):
        return name, getattr(node, "name", None)
    return None, None


def _is_router_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "router":
        return isinstance(func.value, ast.Name) and func.value.id == "lg2m"
    return isinstance(func, ast.Name) and func.id == "router"


def _router_route(call: ast.Call, path: str) -> Route | None:
    if len(call.args) < 2:
        return None
    source = _str_const(call.args[0])
    branches = call.args[1]
    if source is None or not isinstance(branches, (ast.List, ast.Tuple)):
        return None

    pairs: list[tuple[str, str]] = []
    else_target: str | None = None
    for elt in branches.elts:
        if not isinstance(elt, (ast.Tuple, ast.List)) or len(elt.elts) != 2:
            continue
        key_node, target_node = elt.elts
        target = _str_const(target_node)
        if target is None:
            continue
        if _is_else_node(key_node):
            else_target = target
            continue
        key = _str_const(key_node)
        if key is not None:
            pairs.append((key, target))

    return Route(
        source_id=source,
        branches=tuple(pairs),
        else_target=else_target,  # None when the source omits ELSE (diff layer reports it)
        loc=SourceLocation(path, call.lineno),
    )


def _is_else_node(node: ast.expr) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "ELSE" and isinstance(node.value, ast.Name) and node.value.id == "lg2m"
    return isinstance(node, ast.Name) and node.id == "ELSE"


def _callee_name(expr: ast.expr) -> str | None:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return None


def _str_const(expr: ast.expr) -> str | None:
    return expr.value if isinstance(expr, ast.Constant) and isinstance(expr.value, str) else None
