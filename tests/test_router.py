"""The Model-A router spine: AC-05..AC-11, AC-13, AC-14."""

from __future__ import annotations

import pytest

from lg2m.annotations import decorators
from lg2m.annotations.registry import get_registry
from lg2m.annotations.router import ELSE, router

CLASSIFY = [
    ("should_escalate", "escalate_to_human"),
    ("should_auto_resolve", "auto_resolve"),
    (ELSE, "investigate"),
]


def test_path_map_keyed_by_predicate_name():
    """AC-05."""
    r = router("classify_intent", CLASSIFY)
    assert r.path_map == {
        "should_escalate": "escalate_to_human",
        "should_auto_resolve": "auto_resolve",
        "[else]": "investigate",
    }
    assert r.source == "classify_intent"
    assert r.branches == (
        ("should_escalate", "escalate_to_human"),
        ("should_auto_resolve", "auto_resolve"),
    )
    assert r.else_target == "investigate"


def _register_flag_predicates():
    @decorators.predicate("should_escalate")
    def should_escalate(state):
        return state.get("escalate", False)

    @decorators.predicate("should_auto_resolve")
    def should_auto_resolve(state):
        return state.get("auto", False)


def test_path_fn_returns_matched_name():
    """AC-06."""
    _register_flag_predicates()
    r = router("classify_intent", CLASSIFY)
    assert r({"escalate": True}) == "should_escalate"


def test_path_fn_returns_else_when_all_falsy():
    """AC-07."""
    _register_flag_predicates()
    r = router("classify_intent", CLASSIFY)
    assert r({}) == "[else]"


def test_path_fn_first_match_order():
    """AC-08: escalate falsy, auto truthy -> the second predicate's name."""
    _register_flag_predicates()
    r = router("classify_intent", CLASSIFY)
    assert r({"escalate": False, "auto": True}) == "should_auto_resolve"


def test_two_predicates_to_same_target_are_two_keys():
    """AC-13."""
    r = router("src", [("a", "compose_reply"), ("b", "compose_reply"), (ELSE, "compose_reply")])
    assert r.path_map == {"a": "compose_reply", "b": "compose_reply", "[else]": "compose_reply"}


def test_missing_else_rejected():
    """AC-09."""
    with pytest.raises(ValueError, match="missing the required ELSE"):
        router("src", [("a", "t")])


def test_reserved_label_as_predicate_key_rejected():
    """AC-10."""
    with pytest.raises(ValueError, match=r"reserved label"):
        router("src", [("[else]", "t"), (ELSE, "d")])


def test_duplicate_else_rejected():
    """AC-11."""
    with pytest.raises(ValueError, match="more than one ELSE"):
        router("src", [("a", "t"), (ELSE, "d1"), (ELSE, "d2")])


def test_router_is_registered():
    """Task 2.2: the factory registers the selector under its source."""
    r = router("classify_intent", CLASSIFY)
    assert get_registry().routers["classify_intent"].path_fn is r


def test_undefined_predicate_raises_lookup_error_at_call():
    """AC-14: no @predicate registered for a referenced name."""
    r = router("classify_intent", CLASSIFY)  # predicates not registered
    with pytest.raises(LookupError, match="should_escalate"):
        r({"escalate": True})
