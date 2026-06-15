"""GFM table parsing (and emit) for the lg2m Markdown contract.

A GFM table is a header pipe-row, a delimiter row (``| --- | --- |``), then body
pipe-rows until a blank or non-pipe line. The cell splitter is char-scanning so
that an escaped pipe (``\\|``) inside a cell is a literal, not a column break
(e.g. the ``Ticket`` row whose description is ``` `'low'` \\| `'normal'` ```).
"""

from __future__ import annotations

import re

_DELIM_CELL = re.compile(r"^:?-+:?$")


def split_row(line: str) -> list[str]:
    """Split a pipe row into trimmed cells, treating ``\\|`` as a literal pipe.

    The leading and trailing pipes that delimit a GFM row produce empty outer
    cells, which are dropped; genuinely empty interior cells are preserved.
    """
    cells: list[str] = []
    buf: list[str] = []
    s = line.strip()
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n and s[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append("".join(buf))

    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def _is_pipe_row(line: str) -> bool:
    return line.strip().startswith("|")


def _is_delimiter_row(line: str) -> bool:
    if not _is_pipe_row(line):
        return False
    cells = split_row(line)
    return bool(cells) and all(_DELIM_CELL.match(c) for c in cells)


def emit_table(headers: list[str], rows: list[dict[str, str]]) -> list[str]:
    """Render ``(headers, rows)`` as GFM lines, re-escaping ``|`` as ``\\|``.

    Alignment is minimal (single-space padding): the round-trip contract is
    structural (``parse(emit(rows)) == rows``), not byte-exact.
    """
    out = ["| " + " | ".join(_escape(h) for h in headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        out.append("| " + " | ".join(_escape(row.get(h, "")) for h in headers) + " |")
    return out


def _escape(cell: str) -> str:
    return cell.replace("|", "\\|")


def parse_table(lines: list[str]) -> tuple[list[str], list[dict[str, str]]] | None:
    """Return ``(headers, rows)`` for the first GFM table in ``lines``.

    ``rows`` is a list of ``{header: cell}`` dicts; missing trailing cells become
    ``""``. Returns ``None`` if no header+delimiter pair is found.
    """
    for i in range(len(lines) - 1):
        if _is_pipe_row(lines[i]) and _is_delimiter_row(lines[i + 1]):
            headers = split_row(lines[i])
            rows: list[dict[str, str]] = []
            j = i + 2
            while j < len(lines) and _is_pipe_row(lines[j]):
                if _is_delimiter_row(lines[j]):
                    j += 1
                    continue
                cells = split_row(lines[j])
                rows.append(
                    {h: (cells[k] if k < len(cells) else "") for k, h in enumerate(headers)}
                )
                j += 1
            return headers, rows
    return None
