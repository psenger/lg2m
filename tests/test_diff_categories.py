"""Layer 2b Phase 2: drift vocabulary + the DriftReport model."""

from __future__ import annotations

from lg2m.diff.categories import (
    DIAGNOSTIC_MAP,
    HINTS,
    DriftCategory,
    Severity,
    default_severity,
)
from lg2m.ir import DiagnosticKind, SourceLocation
from lg2m.report.model import DriftItem, DriftReport


def test_diagnostic_map_covers_every_diagnostic_kind():
    assert set(DIAGNOSTIC_MAP) == set(DiagnosticKind)


def test_every_category_has_a_hint():
    assert set(HINTS) == set(DriftCategory)


def test_default_severity_prose_is_warning_else_error():
    assert default_severity(DriftCategory.PROSE_DRIFT) is Severity.WARNING
    assert default_severity(DriftCategory.NODE_MISSING_IN_DOC) is Severity.ERROR


def test_clean_report_is_clean_and_exits_zero():
    report = DriftReport(graph_id="g")
    assert report.is_clean
    assert not report.has_errors
    assert report.exit_code == 0


def test_warning_only_report_exits_zero():
    report = DriftReport(graph_id="g")
    report.add(
        DriftItem(DriftCategory.PROSE_DRIFT, Severity.WARNING, "n", "prose differs")
    )
    assert not report.is_clean
    assert not report.has_errors
    assert report.exit_code == 0
    assert report.warnings and not report.errors


def test_error_report_exits_one():
    report = DriftReport(graph_id="g")
    report.add(
        DriftItem(
            DriftCategory.NODE_MISSING_IN_DOC,
            Severity.ERROR,
            "ingest_ticket",
            "node only in code",
            code_loc=SourceLocation("nodes.py", 23),
        )
    )
    assert report.has_errors
    assert report.exit_code == 1
    assert report.errors and not report.warnings
