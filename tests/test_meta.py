"""AC-13 + AC-14: the three metadata mechanisms parsed from the golden fixture."""

from __future__ import annotations

from collections import Counter

from lg2m.ir import MetaKind
from lg2m.parsing import markdown, meta


def _all_meta(golden_md_text):
    doc = markdown.parse_markdown(golden_md_text)
    items = []
    for e in doc.entities:
        items.extend(meta.parse_entity_meta(e.id, e.lines))
    return items


def test_metadata_inventory(golden_md_text):
    """AC-13: 1 TABLE + 4 FENCE + 1 NOTE = 6 items; map_items owns FENCE and NOTE."""
    items = _all_meta(golden_md_text)
    assert len(items) == 6

    kinds = Counter(m.kind for m in items)
    assert kinds[MetaKind.TABLE] == 1
    assert kinds[MetaKind.FENCE] == 4
    assert kinds[MetaKind.NOTE] == 1

    table_owners = {m.owner_id for m in items if m.kind == MetaKind.TABLE}
    fence_owners = {m.owner_id for m in items if m.kind == MetaKind.FENCE}
    note_owners = {m.owner_id for m in items if m.kind == MetaKind.NOTE}
    assert table_owners == {"ingest_ticket"}
    assert fence_owners == {"classify_intent", "escalate_to_human", "map_items", "reduce_items"}
    assert note_owners == {"map_items"}

    map_items_kinds = {m.kind for m in items if m.owner_id == "map_items"}
    assert map_items_kinds == {MetaKind.FENCE, MetaKind.NOTE}


def test_table_meta_folds_to_dict(golden_md_text):
    items = _all_meta(golden_md_text)
    table = next(m for m in items if m.kind == MetaKind.TABLE)
    assert table.data["fan-out"] == "parallel"
    assert table.data["targets"] == "`fetch_history`, `lookup_account`"


def test_fence_payload_decode(golden_md_text):
    """AC-14."""
    items = _all_meta(golden_md_text)
    by_owner = {m.owner_id: m for m in items if m.kind == MetaKind.FENCE}

    assert by_owner["classify_intent"].data == {
        "channel": "enrichment",
        "reducer": "operator.add",
        "merges": "fetch_history,lookup_account",
    }
    assert by_owner["escalate_to_human"].data == {"command_goto": "compose_reply"}
    assert by_owner["map_items"].data == {"send_worker": "process_item", "width": "dynamic"}
    # the value keeps its trailing "(Send)" — split only on ';' and first '='
    assert by_owner["reduce_items"].data["merges"] == "process_item (Send)"


def test_note_is_free_text(golden_md_text):
    items = _all_meta(golden_md_text)
    note = next(m for m in items if m.kind == MetaKind.NOTE)
    assert note.owner_id == "map_items"
    assert isinstance(note.data, str)
    assert "process_item" in note.data
    assert note.data.startswith("Note:")
