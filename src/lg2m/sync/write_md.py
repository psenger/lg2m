"""Surgical prose write-back into the Markdown contract.

Replaces only the *leading prose block* of a ``### entity`` body, leaving the heading,
the metadata table / hidden fence / ``> Note:`` blockquote, and the blank-line structure
around them in place. Prose/meta classification reuses ``markdown.is_prose_line`` so the
parser and the writer share one boundary definition.

v1 supports the contract's shape (prose first, then meta). If prose appears *after* a
meta line (interleaved), the entity is refused rather than guessed at. Multiple entity
edits to one file must be applied bottom-to-top (descending ``entity.start``); the engine
owns that ordering.
"""

from __future__ import annotations

from dataclasses import dataclass

from lg2m.parsing.markdown import Entity, is_prose_line
from lg2m.sync.normalize import normalize_prose, prose_equal


@dataclass(frozen=True)
class MdWriteResult:
    lines: list[str]
    changed: bool
    refused_interleaved: bool = False


def write_prose(md_lines: list[str], entity: Entity, new_prose: str | None) -> MdWriteResult:
    """Return ``md_lines`` with ``entity``'s leading prose block replaced by ``new_prose``."""
    if prose_equal(entity.prose, new_prose):
        return MdWriteResult(md_lines, changed=False)

    body_start, body_end = entity.start + 1, entity.end
    first_meta: int | None = None
    prose_idxs: list[int] = []
    prose_after_meta = False
    for i in range(body_start, body_end):
        if md_lines[i].strip() == "":
            continue
        if is_prose_line(md_lines[i]):
            if first_meta is not None:
                prose_after_meta = True
            prose_idxs.append(i)
        elif first_meta is None:
            first_meta = i

    if prose_after_meta:
        return MdWriteResult(md_lines, changed=False, refused_interleaved=True)

    block = normalize_prose(new_prose).split("\n")
    if prose_idxs:
        new_lines = md_lines[: prose_idxs[0]] + block + md_lines[prose_idxs[-1] + 1 :]
    else:
        insert_at = first_meta if first_meta is not None else body_end
        inserted = block + [""]
        if insert_at == body_start:  # no blank between heading and body: add one
            inserted = ["", *inserted]
        new_lines = md_lines[:insert_at] + inserted + md_lines[insert_at:]

    return MdWriteResult(new_lines, changed=True)
