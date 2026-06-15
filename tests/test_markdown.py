"""AC-04 + section/prose/mermaid-locator behaviour for parsing/markdown.py."""

from __future__ import annotations

from lg2m.parsing import markdown
from lg2m.parsing.markdown import CANONICAL_SECTIONS


def test_frontmatter_graph_id(golden_md_text):
    """AC-04."""
    doc = markdown.parse_markdown(golden_md_text, file="support_pipeline.md")
    assert doc.graph_id == "support_pipeline"


def test_six_canonical_sections_located(golden_md_text):
    doc = markdown.parse_markdown(golden_md_text)
    for name in CANONICAL_SECTIONS:
        assert name in doc.sections, name
    # line ranges are coherent: heading < end, body excludes the heading line
    for sec in doc.sections.values():
        assert sec.start < sec.end


def test_entities_split_by_section(golden_md_text):
    doc = markdown.parse_markdown(golden_md_text)
    nodes = {e.id for e in doc.entities if e.section == "Nodes"}
    preds = {e.id for e in doc.entities if e.section == "Predicates"}
    models = {e.id for e in doc.entities if e.section == "Data Models"}
    assert len(nodes) == 13
    assert preds == {"should_escalate", "should_auto_resolve"}
    assert models == {"PipelineState", "Ticket"}


def test_prose_excludes_structural_lines(golden_md_text):
    doc = markdown.parse_markdown(golden_md_text)

    # should_escalate is pure prose
    se = doc.entity("should_escalate")
    assert se is not None
    assert se.prose.startswith("Selects the escalation branch")
    assert "|" not in se.prose and "<!--" not in se.prose

    # classify_intent prose must exclude its hidden fence
    ci = doc.entity("classify_intent")
    assert "<!-- lg2m:" not in ci.prose
    assert "Fan-in of the parallel enrichment" in ci.prose

    # ingest_ticket prose must exclude its meta table
    it = doc.entity("ingest_ticket")
    assert "fan-out" not in it.prose
    assert "| meta | value |" not in it.prose

    # map_items prose must exclude both its fence and its > Note:
    mi = doc.entity("map_items")
    assert "<!-- lg2m:" not in mi.prose
    assert "> Note:" not in mi.prose
    assert "Note:" not in mi.prose


def test_mermaid_block_located(golden_md_text):
    doc = markdown.parse_markdown(golden_md_text)
    assert doc.mermaid_start is not None
    assert doc.mermaid_lines[0].strip() == "stateDiagram-v2"
    # the block carries the conditional fan-out and the composite state
    body = "\n".join(doc.mermaid_lines)
    assert "classify_intent --> investigate: [else]" in body
    assert "state investigate {" in body
    # the closing fence is not included
    assert "```" not in body
