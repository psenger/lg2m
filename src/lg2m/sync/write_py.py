"""Surgical docstring write-back into a Python source file.

Operates on source *lines*, never ``ast.unparse``: the docstring's line span (from the
AST reader) is the only region touched, so every other line is the original list element
and the rest of the file is byte-identical. Multiple edits to one file must be applied
bottom-to-top (descending start line) so earlier edits do not invalidate later spans;
the engine owns that ordering.

Renders from the canonical normalized prose (always ``\"\"\"``), so writing the same prose
twice is a byte-stable no-op. Raw/byte-prefixed docstrings cannot be round-tripped from
the AST-decoded text and are refused (reported, never corrupted).
"""

from __future__ import annotations

from dataclasses import dataclass

from lg2m.annotations.reader import AnnoRef
from lg2m.sync.normalize import normalize_prose, prose_equal


@dataclass(frozen=True)
class WriteResult:
    source: str
    changed: bool
    skipped_raw_prefix: bool = False


def write_docstring(source: str, ref: AnnoRef, new_prose: str | None) -> WriteResult:
    """Replace or insert ``ref``'s docstring with ``new_prose``; return the new source."""
    if prose_equal(ref.docstring, new_prose):
        return WriteResult(source, changed=False)

    lines = source.split("\n")
    indent = " " * (ref.body_col or 0)
    block = _render_docstring(new_prose, indent)

    if ref.doc_span is not None:
        start, end = ref.doc_span  # 1-based inclusive
        if lines[start - 1].lstrip()[:1] not in ('"', "'"):
            return WriteResult(source, changed=False, skipped_raw_prefix=True)
        new_lines = lines[: start - 1] + block + lines[end:]
    else:
        anchor = (ref.body_lineno or 1) - 1  # 0-based; insert before the first body stmt
        new_lines = lines[:anchor] + block + lines[anchor:]

    return WriteResult("\n".join(new_lines), changed=True)


def _render_docstring(prose: str | None, indent: str) -> list[str]:
    body = _escape(normalize_prose(prose))
    if "\n" not in body:
        return [f'{indent}"""{body}"""']
    inner = [f"{indent}{line}".rstrip() if line else "" for line in body.split("\n")]
    return [f'{indent}"""', *inner, f'{indent}"""']


def _escape(text: str) -> str:
    """Make ``text`` safe inside a ``\"\"\"...\"\"\"`` literal: backslashes, embedded triple
    quotes, and a trailing quote adjacent to the closing fence."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"""', '\\"\\"\\"')
    if text.endswith('"'):
        text = text[:-1] + '\\"'
    return text
