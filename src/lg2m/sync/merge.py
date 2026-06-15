"""The per-entity sync decision: a pure function of the three prose hashes.

Given the stored baseline and the current code/Markdown prose, decide what (if
anything) ``sync`` does for one entity. Hash-only at entity granularity gives the
four base-present cases plus the no-base bootstrap without intra-paragraph merging.

Action directions (``WRITE_CODE`` writes the *docstring*, ``WRITE_MD`` writes the
*Markdown*); the engine derives the source prose and the new baseline from the action.
A directional bootstrap (no base, one side empty) is simply the write that fills the
empty side, so it reuses ``WRITE_CODE``/``WRITE_MD`` rather than a separate action.
"""

from __future__ import annotations

from enum import Enum

from lg2m.sync.normalize import prose_hash


class Action(str, Enum):
    WRITE_CODE = "write_code"  # md -> docstring
    WRITE_MD = "write_md"  # docstring -> md
    ADOPT = "adopt"  # no write; record the agreed hash as the new baseline
    NOOP = "noop"  # nothing to do, and nothing to record
    CONFLICT = "conflict"  # both sides moved apart; refuse unless --prefer


_EMPTY = prose_hash("")


def decide(
    base_hash: str | None,
    code_prose: str | None,
    md_prose: str | None,
    prefer: str | None = None,
) -> Action:
    """Resolve one entity. ``prefer`` is ``"code"``, ``"doc"``, or None."""
    h_code = prose_hash(code_prose)
    h_md = prose_hash(md_prose)

    if base_hash is None:
        if h_code == h_md:
            return Action.ADOPT if h_code != _EMPTY else Action.NOOP
        if h_code == _EMPTY:
            return Action.WRITE_CODE  # md prose fills the empty docstring
        if h_md == _EMPTY:
            return Action.WRITE_MD  # docstring fills the empty Markdown prose
        return _prefer_or_conflict(prefer)

    code_changed = h_code != base_hash
    md_changed = h_md != base_hash
    if not code_changed and not md_changed:
        return Action.NOOP
    if md_changed and not code_changed:
        return Action.WRITE_CODE
    if code_changed and not md_changed:
        return Action.WRITE_MD
    if h_code == h_md:
        return Action.ADOPT  # both moved to the same value: just record it
    return _prefer_or_conflict(prefer)


def _prefer_or_conflict(prefer: str | None) -> Action:
    if prefer == "code":
        return Action.WRITE_MD  # the code docstring wins -> write Markdown from it
    if prefer == "doc":
        return Action.WRITE_CODE  # the Markdown wins -> write the docstring from it
    return Action.CONFLICT
