"""The DriftReport value model (docs/design.md Section 8).

A ``DriftItem`` is one reconciliation finding: a category, a severity, the subject
it is about, a message, the two ``file:line`` locations (code side and doc side,
either may be absent), and an actionable hint. ``DriftReport`` collects them and
answers the two questions ``check`` needs: is it clean, and what is the exit code.
``check`` exits non-zero on any ERROR (docs/design.md Section 11: ``1`` = drift / structural
error; the ``2`` = usage/config code is the CLI's call, not the report's).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lg2m.diff.categories import DriftCategory, Severity
from lg2m.ir import SourceLocation


@dataclass(frozen=True)
class DriftItem:
    category: DriftCategory
    severity: Severity
    subject: str
    message: str
    code_loc: SourceLocation | None = None
    doc_loc: SourceLocation | None = None
    hint: str | None = None


@dataclass
class DriftReport:
    graph_id: str
    items: list[DriftItem] = field(default_factory=list)

    def add(self, item: DriftItem) -> None:
        self.items.append(item)

    @property
    def errors(self) -> list[DriftItem]:
        return [i for i in self.items if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[DriftItem]:
        return [i for i in self.items if i.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.items)

    @property
    def is_clean(self) -> bool:
        return not self.items

    @property
    def exit_code(self) -> int:
        return 1 if self.has_errors else 0
