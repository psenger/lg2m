"""The per-import registry is a resettable assembly buffer."""

from __future__ import annotations

from lg2m.annotations import registry
from lg2m.annotations.registry import NodeEntry, PredicateEntry


def test_get_registry_is_a_singleton():
    assert registry.get_registry() is registry.get_registry()


def test_reset_clears_every_collection():
    reg = registry.get_registry()
    reg.nodes["n"] = NodeEntry("n", lambda s: s, "m", 1)
    reg.predicates["p"] = PredicateEntry("p", lambda s: s, "m", 2)
    reg.models["M"] = None  # type: ignore[assignment]
    reg.routers["r"] = None  # type: ignore[assignment]

    registry.reset()

    assert reg.nodes == {}
    assert reg.predicates == {}
    assert reg.models == {}
    assert reg.routers == {}


def test_entries_are_frozen_value_objects():
    import dataclasses

    import pytest

    entry = NodeEntry("n", lambda s: s, "m", 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.id = "x"  # type: ignore[misc]


# The next two tests both register the id "dup" and each asserts a clean start.
# They pass only because the autouse reset_registry fixture clears the singleton
# between tests; if isolation broke, the second to run would see a leaked entry.


def test_isolation_first():
    reg = registry.get_registry()
    assert reg.nodes == {}
    reg.nodes["dup"] = NodeEntry("dup", lambda s: s, "m", 1)


def test_isolation_second():
    reg = registry.get_registry()
    assert reg.nodes == {}
    reg.nodes["dup"] = NodeEntry("dup", lambda s: s, "m", 1)
