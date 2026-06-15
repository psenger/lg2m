"""Layer 6 Task 2.3: canonical prose normalization (sync/normalize.py)."""

from __future__ import annotations

from lg2m.sync.normalize import normalize_prose, prose_equal, prose_hash


def test_indented_docstring_equals_column_zero_markdown():
    """A body-indented docstring and column-0 Markdown prose normalize equal."""
    docstring = "One.\n\n    Two.\n    "  # first line flush, body indented, trailing pad
    md = "One.\n\nTwo."
    assert prose_equal(docstring, md)
    assert prose_hash(docstring) == prose_hash(md)


def test_crlf_and_trailing_blanks_idempotent():
    a = "Para one.\r\n\r\nPara two.\r\n\r\n\r\n"
    assert normalize_prose(a) == "Para one.\n\nPara two."
    assert normalize_prose(normalize_prose(a)) == normalize_prose(a)


def test_blank_line_runs_collapse_to_one():
    assert normalize_prose("a\n\n\n\nb") == "a\n\nb"


def test_none_and_whitespace_normalize_to_empty():
    assert normalize_prose(None) == ""
    assert normalize_prose("   \n  \n") == ""
    assert prose_equal(None, "")
    assert prose_hash(None) == prose_hash("")
