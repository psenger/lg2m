"""Human-readable rendering of a DriftReport.

A clean report renders one line; a drifted report groups each item with its
severity, category, subject, message, the two ``file:line`` locations, and a hint.
Pure: a total function from ``DriftReport`` to ``str``.
"""

from __future__ import annotations

from lg2m.ir import SourceLocation
from lg2m.report.model import DriftReport


def render_text(report: DriftReport) -> str:
    if report.is_clean:
        return f"{report.graph_id}: clean — 0 drift items"

    lines = [f"{report.graph_id}: {_summary(report)}", ""]
    for item in report.items:
        lines.append(f"{item.severity.value.upper():<7} {item.category.value}  {item.subject}")
        lines.append(f"  {item.message}")
        if item.code_loc is not None:
            lines.append(f"  code: {_loc(item.code_loc)}")
        if item.doc_loc is not None:
            lines.append(f"  doc:  {_loc(item.doc_loc)}")
        if item.hint:
            lines.append(f"  hint: {item.hint}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _summary(report: DriftReport) -> str:
    errors, warnings = len(report.errors), len(report.warnings)
    return f"{errors} error{_s(errors)}, {warnings} warning{_s(warnings)}"


def _s(count: int) -> str:
    return "" if count == 1 else "s"


def _loc(loc: SourceLocation) -> str:
    tail = f":{loc.col}" if loc.col is not None else ""
    return f"{loc.file}:{loc.line}{tail}"
