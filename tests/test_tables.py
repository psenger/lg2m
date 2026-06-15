"""AC-12 + table row counts: GFM table parsing against the golden fixture."""

from __future__ import annotations

from lg2m.parsing import tables


def _section(text: str, heading: str) -> list[str]:
    """Lines from ``heading`` to end-of-text (parse_table takes the first table)."""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    return lines[start:]


def test_split_row_basic():
    assert tables.split_row("| a | b | c |") == ["a", "b", "c"]


def test_split_row_preserves_empty_interior_cell():
    assert tables.split_row("| a |  | c |") == ["a", "", "c"]


def test_escaped_pipe_is_literal_not_a_column(golden_md_text):
    """AC-12: the Ticket priority/customer_tier rows keep literal pipes, 4 cells."""
    rows = tables.parse_table(_section(golden_md_text, "### `Ticket`"))[1]
    by_attr = {r["attribute"]: r for r in rows}
    assert len(rows) == 4
    priority = by_attr["`priority`"]["description"]
    assert "|" in priority
    assert priority == "`'low'` | `'normal'` | `'high'`"
    # every Ticket row has exactly the 4 declared columns
    assert all(set(r) == {"attribute", "type", "reducer", "description"} for r in rows)


def test_index_table_has_15_rows(golden_md_text):
    headers, rows = tables.parse_table(_section(golden_md_text, "## Index"))
    assert headers == ["id", "type"]
    assert len(rows) == 15
    assert sum(1 for r in rows if r["type"] == "node") == 13
    assert sum(1 for r in rows if r["type"] == "predicate") == 2


def test_pipeline_state_table_has_8_rows(golden_md_text):
    headers, rows = tables.parse_table(_section(golden_md_text, "### `PipelineState`"))
    assert headers == ["attribute", "type", "reducer", "description"]
    assert len(rows) == 8


def test_edges_table_has_17_rows(golden_md_text):
    headers, rows = tables.parse_table(_section(golden_md_text, "## Edges"))
    assert headers == ["from", "to", "label", "kind", "notes"]
    assert len(rows) == 17
    # blank label cells survive as empty strings, not None
    assert all(isinstance(r["label"], str) for r in rows)
    labelled = {r["label"] for r in rows if r["label"]}
    assert labelled == {"`should_escalate`", "`should_auto_resolve`", "`[else]`"}


def test_no_table_returns_none():
    assert tables.parse_table(["just prose", "more prose"]) is None


def test_emit_then_parse_round_trips_ticket_table(golden_md_text):
    """Task 2.2: emit -> parse yields identical row dicts (escaped pipes survive)."""
    headers, rows = tables.parse_table(_section(golden_md_text, "### `Ticket`"))
    emitted = tables.emit_table(headers, rows)
    headers2, rows2 = tables.parse_table(emitted)
    assert headers2 == headers
    assert rows2 == rows
    # the literal pipe is preserved through the cycle
    assert "|" in {r["attribute"]: r for r in rows2}["`priority`"]["description"]
