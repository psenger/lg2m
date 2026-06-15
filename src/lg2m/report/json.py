"""Machine-readable rendering of a DriftReport (``check --format json``).

``to_dict`` is the stable shape; ``render_json`` is its serialization. Pure and
framework-free.
"""

from __future__ import annotations

import json as _json
from typing import Any

from lg2m.ir import SourceLocation
from lg2m.report.model import DriftItem, DriftReport


def render_json(report: DriftReport, *, indent: int | None = 2) -> str:
    return _json.dumps(to_dict(report), indent=indent)


def to_dict(report: DriftReport) -> dict[str, Any]:
    return {
        "graph_id": report.graph_id,
        "exit_code": report.exit_code,
        "items": [_item(item) for item in report.items],
    }


def _item(item: DriftItem) -> dict[str, Any]:
    return {
        "category": item.category.value,
        "severity": item.severity.value,
        "subject": item.subject,
        "message": item.message,
        "code_loc": _loc(item.code_loc),
        "doc_loc": _loc(item.doc_loc),
        "hint": item.hint,
    }


def _loc(loc: SourceLocation | None) -> dict[str, Any] | None:
    if loc is None:
        return None
    return {"file": loc.file, "line": loc.line, "col": loc.col}
