"""AST reader: AC-15, AC-16, AC-17, AC-18, AC-19, plus the location merge.

The reader parses the example files as TEXT and never imports them. Since layer 3
installs langgraph, the "never imports" claim is asserted hermetically (a fresh
subprocess), so it is not polluted by other tests that import the example.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from lg2m.annotations import decorators, reader
from lg2m.annotations.registry import get_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "examples" / "support_pipeline" / "src" / "support_pipeline"
ROUTING = SRC / "routing.py"
PREDICATES = SRC / "predicates.py"
STATE = SRC / "state.py"
NODES = SRC / "nodes.py"

NODE_IDS = {
    "ingest_ticket", "fetch_history", "lookup_account", "classify_intent", "auto_resolve",
    "escalate_to_human", "map_items", "process_item", "reduce_items", "compose_reply",
    "gather_logs", "analyze",
}


def test_reader_recovers_route_from_routing(golden_md_text):
    """AC-15."""
    result = reader.read_file(ROUTING)
    assert len(result.routers) == 1
    route = result.routers[0]
    assert route.source_id == "classify_intent"
    assert route.branches == (
        ("should_escalate", "escalate_to_human"),
        ("should_auto_resolve", "auto_resolve"),
    )
    assert route.else_target == "investigate"
    assert route.loc.file == str(ROUTING)
    assert route.loc.line == 33


def test_reader_recovers_predicates():
    """AC-16."""
    refs = {(r.kind, r.key): r for r in reader.read_file(PREDICATES).annotations}
    assert refs[("predicate", "should_escalate")].loc.line == 20
    assert refs[("predicate", "should_auto_resolve")].loc.line == 26


def test_reader_recovers_models_by_kind():
    """AC-17."""
    refs = {(r.kind, r.key): r for r in reader.read_file(STATE).annotations}
    assert refs[("data_model", "Ticket")].loc.line == 41
    assert refs[("state_model", "PipelineState")].loc.line == 51


def test_reader_recovers_twelve_nodes_without_importing():
    """AC-18."""
    annos = reader.read_file(NODES).annotations
    nodes = [r for r in annos if r.kind == "node"]
    assert len(nodes) == 12
    ids = {r.key for r in nodes}
    assert ids == NODE_IDS
    assert "investigate" not in ids  # the subgraph carries no @node
    by_id = {r.key: r for r in nodes}
    assert by_id["ingest_ticket"].loc.line == 23
    assert by_id["analyze"].loc.line == 130


def test_reader_does_not_import_the_module():
    """AC-18 (hermetic): nodes.py imports langgraph; a pure-AST read never triggers it.

    Run in a subprocess so the assertion is not polluted by other tests in this session
    that import the example (and thus langgraph).
    """
    code = (
        "import sys; from lg2m.annotations import reader; "
        f"reader.read_file({str(NODES)!r}); "
        "assert 'langgraph' not in sys.modules; "
        "assert 'support_pipeline.nodes' not in sys.modules"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_reader_handles_both_else_spellings(tmp_path):
    """AC-19."""
    attr_form = tmp_path / "attr.py"
    attr_form.write_text(
        'import lg2m\nr = lg2m.router("s", [("a", "t"), (lg2m.ELSE, "d")])\n', encoding="utf-8"
    )
    name_form = tmp_path / "name.py"
    name_form.write_text(
        'from lg2m import router, ELSE\nr = router("s", [("a", "t"), (ELSE, "d")])\n',
        encoding="utf-8",
    )
    attr_else = reader.read_file(attr_form).routers[0].else_target
    name_else = reader.read_file(name_form).routers[0].else_target
    assert attr_else == name_else == "d"


def test_reader_captures_multiline_docstring(tmp_path):
    """Layer 6 Task 2.1: a multi-line docstring is captured with a >1-line span."""
    f = tmp_path / "m.py"
    f.write_text(
        'from lg2m import node\n'
        '@node("a")\n'
        'def a(state):\n'
        '    """Line one.\n'
        '\n'
        '    Line two.\n'
        '    """\n'
        '    return state\n',
        encoding="utf-8",
    )
    ref = {(r.kind, r.key): r for r in reader.read_file(f).annotations}[("node", "a")]
    assert ref.docstring is not None
    assert "Line one." in ref.docstring and "Line two." in ref.docstring
    assert ref.doc_span is not None
    start, end = ref.doc_span
    assert end > start
    assert ref.body_col == 4


def test_reader_captures_single_line_docstring(tmp_path):
    """Layer 6 Task 2.1: a single-line docstring has start == end and is captured."""
    f = tmp_path / "s.py"
    f.write_text(
        'from lg2m import predicate\n'
        '@predicate("p")\n'
        'def p(state):\n'
        '    """One liner."""\n'
        '    return True\n',
        encoding="utf-8",
    )
    ref = {(r.kind, r.key): r for r in reader.read_file(f).annotations}[("predicate", "p")]
    assert ref.docstring == "One liner."
    assert ref.doc_span is not None
    start, end = ref.doc_span
    assert start == end
    assert ref.body_col == 4


def test_reader_no_docstring_has_none_span(tmp_path):
    """Layer 6 Task 2.1: no docstring -> doc_span None, body_col still set (insert point)."""
    f = tmp_path / "n.py"
    f.write_text(
        'from lg2m import node\n'
        '@node("a")\n'
        'def a(state):\n'
        '    return state\n',
        encoding="utf-8",
    )
    ref = {(r.kind, r.key): r for r in reader.read_file(f).annotations}[("node", "a")]
    assert ref.docstring is None
    assert ref.doc_span is None
    assert ref.body_col == 4


def test_merge_locations_keys_by_registry_membership():
    """Task 3.3: merge attaches reader locations only for registered annotations."""

    @decorators.predicate("should_escalate")
    def should_escalate(state):
        return state

    @decorators.predicate("should_auto_resolve")
    def should_auto_resolve(state):
        return state

    result = reader.read_file(PREDICATES)
    locations = reader.merge_locations(result, get_registry())
    assert locations[("predicate", "should_escalate")].line == 20
    assert locations[("predicate", "should_auto_resolve")].line == 26
    # an annotation the registry does not know about is excluded
    assert all(kind == "predicate" for (kind, _key) in locations)
