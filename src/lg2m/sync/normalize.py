"""Canonical prose normalization shared by the drift check and ``sync``.

Prose lives column-0 in the Markdown contract but body-indented in a docstring, with
varying line endings, leading/trailing blank lines, and blank-line runs. To compare
or round-trip the two stores they must reduce to one canonical form, defined here once
so the drift check (``diff/engine._check_prose``) and ``sync`` cannot disagree.

Canonical form (in order): CRLF/CR -> LF; ``inspect.cleandoc`` (strip the first line,
dedent the rest by their common indent, drop leading/trailing blank lines, expand
tabs); per-line right-strip; collapse blank-line runs to one (matching the Markdown
parser's ``_extract_prose``); final strip.
"""

from __future__ import annotations

import hashlib
import inspect


def normalize_prose(text: str | None) -> str:
    """Reduce a docstring or Markdown paragraph to its canonical comparable form."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = inspect.cleandoc(text)
    out: list[str] = []
    prev_blank = False
    for line in text.split("\n"):
        line = line.rstrip()
        blank = not line
        if blank and prev_blank:
            continue
        out.append(line)
        prev_blank = blank
    return "\n".join(out).strip()


def prose_hash(text: str | None) -> str:
    """sha256 hex of the normalized prose; the unit stored in ``.lg2m.lock``."""
    return hashlib.sha256(normalize_prose(text).encode("utf-8")).hexdigest()


def prose_equal(a: str | None, b: str | None) -> bool:
    """True when two prose values are equal after normalization."""
    return normalize_prose(a) == normalize_prose(b)
