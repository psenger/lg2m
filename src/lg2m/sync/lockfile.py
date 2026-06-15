"""The ``.lg2m.lock`` baseline store: per-entity hash of the last-synced prose.

A committed JSON file (stdlib only; the project has no TOML writer) keyed
graph -> bucket -> entity:

    {"version": 1,
     "graphs": {"<gid>": {"nodes":      {"<id>":   {"base_hash": "<sha256>"}},
                          "predicates": {"<name>": {"base_hash": "<sha256>"}}}}}

The per-entity value is an object, not a bare string, so a future ``base_text``
(for a true 3-way merge) can be added without a format break. Serialization is
``sort_keys=True`` so the file is diff-friendly and byte-stable across re-writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOCK_VERSION = 1
_BUCKETS = {"node": "nodes", "predicate": "predicates"}


@dataclass
class Lock:
    """In-memory view of the lockfile; ``graphs`` mirrors the on-disk JSON shape."""

    graphs: dict[str, Any] = field(default_factory=dict)
    version: int = LOCK_VERSION


def load_lock(path: Path) -> Lock:
    """Return the lock at ``path``, or an empty lock when the file does not exist."""
    if not path.exists():
        return Lock()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Lock(graphs=raw.get("graphs", {}), version=raw.get("version", LOCK_VERSION))


def dumps_lock(lock: Lock) -> str:
    """The canonical serialized form (sorted keys, trailing newline)."""
    payload = {"version": lock.version, "graphs": lock.graphs}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_lock(path: Path, lock: Lock) -> None:
    """Serialize ``lock`` deterministically to ``path``."""
    path.write_text(dumps_lock(lock), encoding="utf-8")


def base_hash(lock: Lock, gid: str, kind: str, key: str) -> str | None:
    """The stored base hash for one entity, or None if never synced."""
    entry = lock.graphs.get(gid, {}).get(_BUCKETS[kind], {}).get(key, {})
    return entry.get("base_hash")


def set_base(lock: Lock, gid: str, kind: str, key: str, h: str) -> None:
    """Record (or update) the base hash for one entity."""
    bucket = lock.graphs.setdefault(gid, {}).setdefault(_BUCKETS[kind], {})
    bucket.setdefault(key, {})["base_hash"] = h
