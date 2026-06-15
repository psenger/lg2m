"""Layer 6 Task 3.1: the .lg2m.lock baseline store (sync/lockfile.py)."""

from __future__ import annotations

from lg2m.sync.lockfile import Lock, base_hash, load_lock, set_base, write_lock


def test_load_missing_returns_empty_lock(tmp_path):
    lock = load_lock(tmp_path / "nope.lock")
    assert lock.graphs == {}
    assert base_hash(lock, "g", "node", "n") is None


def test_set_and_get_base_round_trips_through_disk(tmp_path):
    lock = Lock()
    set_base(lock, "g", "node", "n", "abc")
    set_base(lock, "g", "predicate", "p", "def")
    assert base_hash(lock, "g", "node", "n") == "abc"
    assert base_hash(lock, "g", "predicate", "p") == "def"

    path = tmp_path / "x.lock"
    write_lock(path, lock)
    reloaded = load_lock(path)
    assert base_hash(reloaded, "g", "node", "n") == "abc"
    assert base_hash(reloaded, "g", "predicate", "p") == "def"


def test_write_is_byte_stable_across_reload(tmp_path):
    lock = Lock()
    set_base(lock, "g", "node", "n", "h1")
    set_base(lock, "g", "predicate", "p", "h2")
    first, second = tmp_path / "a.lock", tmp_path / "b.lock"
    write_lock(first, lock)
    write_lock(second, load_lock(first))
    assert first.read_text() == second.read_text()


def test_key_order_is_deterministic(tmp_path):
    a = Lock()
    set_base(a, "g", "node", "z", "1")
    set_base(a, "g", "node", "a", "2")
    b = Lock()
    set_base(b, "g", "node", "a", "2")
    set_base(b, "g", "node", "z", "1")
    pa, pb = tmp_path / "a.lock", tmp_path / "b.lock"
    write_lock(pa, a)
    write_lock(pb, b)
    assert pa.read_text() == pb.read_text()
