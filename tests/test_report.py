"""Layer 2b Phase 6: text + json rendering of a DriftReport."""

from __future__ import annotations

import json

from lg2m.diff.categories import DriftCategory, Severity
from lg2m.ir import SourceLocation
from lg2m.report import render_json, render_text
from lg2m.report.model import DriftItem, DriftReport


def _drifted() -> DriftReport:
    report = DriftReport(graph_id="support_pipeline")
    report.add(
        DriftItem(
            DriftCategory.ROUTE_TARGET_MISMATCH,
            Severity.ERROR,
            "classify_intent",
            "mapping != diagram",
            code_loc=SourceLocation("routing.py", 33),
            doc_loc=SourceLocation("support_pipeline.md", 45),
            hint="mapping and diagram aim a branch at different targets",
        )
    )
    report.add(
        DriftItem(DriftCategory.PROSE_DRIFT, Severity.WARNING, "ingest_ticket", "prose differs")
    )
    return report


def test_text_clean():
    text = render_text(DriftReport(graph_id="g"))
    assert "0 drift items" in text


def test_text_drifted_lists_items_with_both_locs():
    text = render_text(_drifted())
    assert "1 error, 1 warning" in text
    assert "route_target_mismatch" in text
    assert "code: routing.py:33" in text
    assert "doc:  support_pipeline.md:45" in text
    assert "hint: " in text


def test_json_clean_round_trips():
    payload = json.loads(render_json(DriftReport(graph_id="g")))
    assert payload == {"graph_id": "g", "exit_code": 0, "items": []}


def test_json_drifted_round_trips():
    payload = json.loads(render_json(_drifted()))
    assert payload["graph_id"] == "support_pipeline"
    assert payload["exit_code"] == 1
    assert len(payload["items"]) == 2

    route = payload["items"][0]
    assert route["category"] == "route_target_mismatch"
    assert route["severity"] == "error"
    assert route["code_loc"] == {"file": "routing.py", "line": 33, "col": None}
    assert route["doc_loc"] == {"file": "support_pipeline.md", "line": 45, "col": None}

    prose = payload["items"][1]
    assert prose["code_loc"] is None and prose["doc_loc"] is None
