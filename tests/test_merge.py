"""Layer 6 Task 4.1: the pure per-entity merge decision table (sync/merge.py)."""

from __future__ import annotations

from lg2m.sync.merge import Action, decide
from lg2m.sync.normalize import prose_hash

BASE = prose_hash("original")


# --- base present: the four cases --------------------------------------------


def test_base_present_neither_changed_is_noop():
    assert decide(BASE, "original", "original") is Action.NOOP


def test_base_present_only_md_changed_writes_docstring():
    assert decide(BASE, "original", "new prose") is Action.WRITE_CODE


def test_base_present_only_code_changed_writes_markdown():
    assert decide(BASE, "new prose", "original") is Action.WRITE_MD


def test_base_present_both_changed_apart_is_conflict():
    assert decide(BASE, "code side", "doc side") is Action.CONFLICT


def test_base_present_both_changed_to_same_value_is_adopt():
    assert decide(BASE, "converged", "converged") is Action.ADOPT


# --- no base: the three bootstrap cases --------------------------------------


def test_no_base_both_equal_nonempty_is_adopt():
    assert decide(None, "same", "same") is Action.ADOPT


def test_no_base_both_empty_is_noop():
    assert decide(None, None, None) is Action.NOOP
    assert decide(None, "", "   ") is Action.NOOP


def test_no_base_code_empty_md_prose_writes_docstring():
    assert decide(None, None, "from markdown") is Action.WRITE_CODE


def test_no_base_md_empty_code_prose_writes_markdown():
    assert decide(None, "from docstring", None) is Action.WRITE_MD


def test_no_base_both_nonempty_unequal_is_conflict():
    assert decide(None, "a", "b") is Action.CONFLICT


# --- --prefer resolves a conflict --------------------------------------------


def test_prefer_code_writes_markdown():
    assert decide(BASE, "code side", "doc side", prefer="code") is Action.WRITE_MD


def test_prefer_doc_writes_docstring():
    assert decide(BASE, "code side", "doc side", prefer="doc") is Action.WRITE_CODE


def test_prefer_resolves_no_base_conflict_too():
    assert decide(None, "a", "b", prefer="code") is Action.WRITE_MD
    assert decide(None, "a", "b", prefer="doc") is Action.WRITE_CODE
