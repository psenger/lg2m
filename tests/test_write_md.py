"""Layer 6 Task 5.2: surgical Markdown prose write-back (sync/write_md.py)."""

from __future__ import annotations

from lg2m.parsing.markdown import parse_markdown
from lg2m.sync.normalize import prose_equal
from lg2m.sync.write_md import write_prose

FENCE_DOC = (
    "## Nodes\n"
    "\n"
    "### `n`\n"
    "\n"
    "Old prose about n.\n"
    "\n"
    "<!-- lg2m: channel=enrichment -->\n"
)

NOTE_DOC = (
    "## Nodes\n"
    "\n"
    "### `n`\n"
    "\n"
    "Old prose.\n"
    "\n"
    "> Note: a human-only aside.\n"
)


def _entity(text, eid="n"):
    return parse_markdown(text).entity(eid)


def test_replace_preserves_following_fence():
    lines = FENCE_DOC.splitlines()
    result = write_prose(lines, _entity(FENCE_DOC), "Brand new prose.")
    assert result.changed
    joined = "\n".join(result.lines)
    assert "Brand new prose." in joined
    assert "Old prose about n." not in joined
    assert "<!-- lg2m: channel=enrichment -->" in joined
    # re-parsing recovers the new prose and still excludes the fence from it
    reparsed = _entity(joined)
    assert prose_equal(reparsed.prose, "Brand new prose.")
    assert "<!--" not in reparsed.prose


def test_replace_preserves_following_note():
    lines = NOTE_DOC.splitlines()
    result = write_prose(lines, _entity(NOTE_DOC), "Replaced prose.")
    joined = "\n".join(result.lines)
    assert "Replaced prose." in joined
    assert "> Note: a human-only aside." in joined
    assert prose_equal(_entity(joined).prose, "Replaced prose.")


def test_rewrite_is_idempotent_byte_identical():
    lines = FENCE_DOC.splitlines()
    once = write_prose(lines, _entity(FENCE_DOC), "Stable prose.").lines
    entity2 = _entity("\n".join(once))
    twice = write_prose(once, entity2, "Stable prose.")
    assert twice.changed is False
    assert twice.lines == once


def test_no_op_when_prose_unchanged():
    lines = FENCE_DOC.splitlines()
    result = write_prose(lines, _entity(FENCE_DOC), "Old prose about n.")
    assert result.changed is False
    assert result.lines == lines


def test_insert_prose_when_entity_has_only_meta():
    doc = (
        "## Nodes\n"
        "\n"
        "### `n`\n"
        "\n"
        "<!-- lg2m: k=v -->\n"
    )
    result = write_prose(doc.splitlines(), _entity(doc), "Inserted prose.")
    assert result.changed
    joined = "\n".join(result.lines)
    assert "Inserted prose." in joined
    assert "<!-- lg2m: k=v -->" in joined
    assert joined.index("Inserted prose.") < joined.index("<!-- lg2m")  # prose before meta
    assert prose_equal(_entity(joined).prose, "Inserted prose.")


def test_interleaved_prose_after_meta_is_refused():
    doc = (
        "## Nodes\n"
        "\n"
        "### `n`\n"
        "\n"
        "Leading prose.\n"
        "\n"
        "| meta | value |\n"
        "\n"
        "Trailing prose after the table.\n"
    )
    result = write_prose(doc.splitlines(), _entity(doc), "New prose.")
    assert result.refused_interleaved is True
    assert result.changed is False
