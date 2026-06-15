"""Layer 3 Phase 4: load_compiled imports + runs the factory at the untrusted boundary."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from lg2m.annotations.registry import get_registry
from lg2m.config import loader
from lg2m.discovery.resolve import ResolvedGraph, resolve
from lg2m.introspect.loader import load_compiled
from lg2m.ir import DiagnosticKind


def test_missing_module_yields_import_failure_not_exception():
    resolved = ResolvedGraph(
        "g", "no_such_module_xyz", "build_graph", Path("/x.md"), (), True, "langgraph"
    )
    loaded = load_compiled(resolved)
    assert loaded.compiled is None
    assert len(loaded.diagnostics) == 1
    assert loaded.diagnostics[0].kind is DiagnosticKind.IMPORT_FAILURE
    assert loaded.diagnostics[0].subject == "g"


def _drop_example_modules():
    """Force a fresh import so the decorators repopulate the (reset) registry."""
    stale = [m for m in sys.modules if m == "support_pipeline" or m.startswith("support_pipeline.")]
    for name in stale:
        del sys.modules[name]


@pytest.mark.langgraph
def test_loads_real_graph_and_populates_registry(golden_toml_path):
    graphs = loader.load(golden_toml_path)
    resolved = resolve(
        graphs["support_pipeline"], base_dir=golden_toml_path.parent, graph_id="support_pipeline"
    )
    _drop_example_modules()
    loaded = load_compiled(resolved)

    assert loaded.diagnostics == []
    assert loaded.compiled is not None

    reg = get_registry()
    assert len(reg.nodes) == 12
    assert len(reg.models) == 2
    assert set(reg.routers) == {"classify_intent"}
    # predicates.py is NOT in graph.py's import chain (the Model-A router resolves
    # predicate names lazily and never imports them), so the @predicate functions are
    # not live here. The pipeline discovers them via the AST reader, not the live import.
    assert len(reg.predicates) == 0
