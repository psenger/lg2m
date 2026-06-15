"""Layer 2b Phase 1: the introspection seam is substitutable and framework-free."""

from __future__ import annotations

import subprocess
import sys

from lg2m.introspect import FakeIntrospector, GraphIntrospector
from lg2m.ir import GraphModel, Node

# Modules that must import no framework even though lg2m.pipeline.check() lazy-imports the adapter.
_FRAMEWORK_FREE_IMPORTS = (
    "import sys, lg2m, lg2m.introspect, lg2m.diff.engine, lg2m.report, lg2m.pipeline"
)


def test_fake_returns_its_model():
    gm = GraphModel(graph_id="g", origin="code")
    gm.nodes["a"] = Node(id="a")
    fake = FakeIntrospector(gm)
    assert fake.introspect("g") is gm


def test_fake_satisfies_protocol():
    fake = FakeIntrospector(GraphModel(graph_id="g", origin="code"))
    assert isinstance(fake, GraphIntrospector)


def test_importing_lg2m_pulls_in_no_framework():
    """Hermetic: a fresh interpreter importing lg2m + its layers imports no framework.

    Run in a subprocess so it is unaffected by other tests in this session that import
    langgraph (the adapter is the only module that may, and it is imported lazily inside
    ``check()``). Installed-but-not-imported is the property we assert.
    """
    code = (
        f"{_FRAMEWORK_FREE_IMPORTS}; "
        "roots = {'langgraph', 'langchain_core'}; "
        "leaked = sorted(m for m in sys.modules if m.split('.')[0] in roots); "
        "assert not leaked, leaked"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
