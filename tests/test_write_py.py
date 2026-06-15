"""Layer 6 Task 5.1: surgical docstring write-back (sync/write_py.py)."""

from __future__ import annotations

from lg2m.annotations import reader
from lg2m.sync.normalize import prose_equal
from lg2m.sync.write_py import write_docstring


def _ref(tmp_path, source, key="n", kind="node"):
    f = tmp_path / "m.py"
    f.write_text(source, encoding="utf-8")
    refs = {(r.kind, r.key): r for r in reader.read_file(f).annotations}
    return refs[(kind, key)]


def test_insert_into_function_without_docstring(tmp_path):
    src = (
        'from lg2m import node\n'
        '@node("n")\n'
        'def n(state):\n'
        '    return state\n'
    )
    result = write_docstring(src, _ref(tmp_path, src), "Fresh prose.")
    assert result.changed
    assert '    """Fresh prose."""' in result.source
    assert "def n(state):" in result.source
    assert "    return state" in result.source
    # re-reading the written source recovers the prose
    again = _ref(tmp_path, result.source)
    assert prose_equal(again.docstring, "Fresh prose.")


def test_replace_multiline_docstring(tmp_path):
    src = (
        'from lg2m import node\n'
        '@node("n")\n'
        'def n(state):\n'
        '    """Old line one.\n'
        '\n'
        '    Old line two.\n'
        '    """\n'
        '    return state\n'
    )
    result = write_docstring(src, _ref(tmp_path, src), "New para.\n\nSecond para.")
    assert result.changed
    assert "Old line one." not in result.source
    assert "New para." in result.source and "Second para." in result.source
    assert "    return state" in result.source


def test_replace_single_line_docstring(tmp_path):
    src = (
        'from lg2m import predicate\n'
        '@predicate("p")\n'
        'def p(state):\n'
        '    """Old."""\n'
        '    return True\n'
    )
    result = write_docstring(src, _ref(tmp_path, src, key="p", kind="predicate"), "New one liner.")
    assert result.changed
    assert '    """New one liner."""' in result.source
    assert "Old." not in result.source


def test_rewrite_is_idempotent_and_byte_identical(tmp_path):
    src = (
        'from lg2m import node\n'
        '@node("n")\n'
        'def n(state):\n'
        '    return state\n'
    )
    once = write_docstring(src, _ref(tmp_path, src), "Stable prose.").source
    twice = write_docstring(once, _ref(tmp_path, once), "Stable prose.")
    assert twice.changed is False
    assert twice.source == once


def test_lines_outside_the_span_are_unchanged(tmp_path):
    src = (
        'HEADER = 1\n'
        'from lg2m import node\n'
        '@node("n")\n'
        'def n(state):\n'
        '    """Old."""\n'
        '    return state\n'
        'FOOTER = 2\n'
    )
    out = write_docstring(src, _ref(tmp_path, src), "New.").source.split("\n")
    assert out[0] == "HEADER = 1"
    assert "FOOTER = 2" in out
    assert "    return state" in out


def test_escapes_embedded_quotes_and_backslashes(tmp_path):
    src = (
        'from lg2m import node\n'
        '@node("n")\n'
        'def n(state):\n'
        '    return state\n'
    )
    prose = 'Backslash \\ and a triple quote """ and a trailing quote "'
    result = write_docstring(src, _ref(tmp_path, src), prose)
    assert result.changed
    again = _ref(tmp_path, result.source)  # the written file parses and round-trips
    assert prose_equal(again.docstring, prose)


def test_raw_prefixed_docstring_is_refused(tmp_path):
    src = (
        'from lg2m import node\n'
        '@node("n")\n'
        'def n(state):\n'
        '    r"""Raw \\d docstring."""\n'
        '    return state\n'
    )
    result = write_docstring(src, _ref(tmp_path, src), "Should not be written.")
    assert result.skipped_raw_prefix is True
    assert result.changed is False
    assert result.source == src
