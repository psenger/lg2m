"""Layer 5 / Phase 2: ``gen --from-code`` Markdown emission (docs/design.md Sections 10, 14).

Framework-free unit tests over ``scaffold.generate_markdown`` (the emitted contract re-parses to a
structurally equal IR; sections present; prose is ``TODO``), plus the ``@pytest.mark.langgraph``
golden (code -> markdown -> IR on the minimal fixture) and a lenient smoke on the full
``support_pipeline`` example (whose subgraph / Send / Command do not round-trip in v1).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from _roundtrip import introspect_generated, structural_key
from lg2m.diff.assemble import assemble_code_model, assemble_doc_model
from lg2m.parsing.markdown import parse_markdown
from lg2m.pipeline import gather_annotations
from lg2m.scaffold import generate_code, generate_markdown

REPO_ROOT = Path(__file__).resolve().parent.parent
_SECTIONS = ("## Index", "## Graph", "## Data Models", "## Predicates", "## Nodes", "## Edges")


def _doc_model(text: str):
    name = "mini_pipeline.md"
    return assemble_doc_model(parse_markdown(text, file=name), file=name)


# --- framework-free unit tests -----------------------------------------------


def test_markdown_round_trips_structurally(mini_md_text):
    model = _doc_model(mini_md_text)
    emitted = generate_markdown(model)
    reparsed = assemble_doc_model(parse_markdown(emitted, file="gen.md"), file="gen.md")
    assert reparsed.diagnostics == []
    assert structural_key(reparsed) == structural_key(model)


def test_all_canonical_sections_present(mini_md_text):
    emitted = generate_markdown(_doc_model(mini_md_text))
    for section in _SECTIONS:
        assert section in emitted
    assert emitted.startswith("---\nlg2m_graph: mini_pipeline\n---")
    assert "```mermaid" in emitted


def test_prose_is_todo_and_state_marker_round_trips(mini_md_text):
    emitted = generate_markdown(_doc_model(mini_md_text))
    assert emitted.count("TODO: describe this node.") == 8
    assert emitted.count("TODO: describe this predicate.") == 2
    # the @state_model / @data_model markers are what make is_graph_state round-trip
    assert "(`@state_model`)" in emitted
    assert "(`@data_model`)" in emitted


def test_importing_markdown_emitter_pulls_in_no_framework():
    snippet = (
        "import sys, lg2m.scaffold.markdown; "
        "assert 'langgraph' not in sys.modules, 'markdown emitter imported langgraph'"
    )
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- goldens (framework) -----------------------------------------------------


@pytest.mark.langgraph
def test_golden_code_to_markdown_to_ir(mini_md_text, tmp_path):
    code = introspect_generated(generate_code(_doc_model(mini_md_text)), tmp_path, "mini_pipeline")
    emitted = generate_markdown(code)
    reparsed = assemble_doc_model(parse_markdown(emitted, file="gen.md"), file="gen.md")
    assert structural_key(reparsed) == structural_key(code)


@pytest.mark.langgraph
def test_example_smoke_is_well_sectioned(golden_compiled, golden_src_dir):
    from lg2m.annotations.registry import get_registry
    from lg2m.introspect.langgraph_adapter import LangGraphIntrospector

    topology = LangGraphIntrospector(
        golden_compiled, xray=True, registry=get_registry()
    ).introspect("support_pipeline")
    registry, locations = gather_annotations(golden_src_dir)
    code = assemble_code_model(topology, registry, locations)

    emitted = generate_markdown(code)
    for section in _SECTIONS:
        assert section in emitted
    # it parses without error even though the subgraph's flattened ``:`` ids do not round-trip
    assert parse_markdown(emitted, file="ex.md").graph_id == "support_pipeline"
