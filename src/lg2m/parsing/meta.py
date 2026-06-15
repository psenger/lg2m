"""The three metadata mechanisms the lg2m diagram cannot draw (docs/design.md Section 7).

Each is attached to the entity (node/predicate) whose ``### `` block it sits in:

1. ``MetaKind.TABLE`` — a visible ``| meta | value |`` table; folded to a dict.
2. ``MetaKind.FENCE`` — a hidden ``<!-- lg2m: k=v; k=v -->`` comment; the body is
   split on ``;`` into pairs and on the first ``=`` into key/value (so a value may
   itself contain ``=``, ``,`` or ``(...)``, e.g. ``merges=process_item (Send)``).
3. ``MetaKind.NOTE`` — a ``> Note:`` blockquote; kept as free text, never decoded.

An entity may own more than one (``map_items`` owns both a FENCE and a NOTE), so
results are a flat list keyed by ``owner_id``.
"""

from __future__ import annotations

import re

from lg2m.ir import Meta, MetaKind
from lg2m.parsing import tables

_FENCE_RE = re.compile(r"<!--\s*lg2m:\s*(.*?)\s*-->")


def parse_entity_meta(owner_id: str, lines: list[str]) -> list[Meta]:
    """Return every metadata item declared in one entity's body lines."""
    metas: list[Meta] = []

    parsed = tables.parse_table(lines)
    if parsed is not None:
        headers, rows = parsed
        if headers == ["meta", "value"]:
            metas.append(Meta(owner_id, MetaKind.TABLE, {r["meta"]: r["value"] for r in rows}))

    for line in lines:
        match = _FENCE_RE.search(line.strip())
        if match:
            metas.append(Meta(owner_id, MetaKind.FENCE, _parse_fence_body(match.group(1))))

    note = _collect_note(lines)
    if note is not None:
        metas.append(Meta(owner_id, MetaKind.NOTE, note))

    return metas


def _parse_fence_body(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in body.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        key, sep, value = pair.partition("=")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _collect_note(lines: list[str]) -> str | None:
    quoted = [ln.strip()[1:].strip() for ln in lines if ln.strip().startswith(">")]
    if not quoted:
        return None
    return "\n".join(quoted).strip()
