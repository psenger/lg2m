"""AC-20: the public authoring API is exported and importing lg2m pulls in no framework."""

from __future__ import annotations


def test_authoring_api_is_exported():
    import lg2m

    for name in ("node", "predicate", "router", "ELSE", "state_model", "data_model"):
        assert hasattr(lg2m, name), name
        assert name in lg2m.__all__


def test_importing_lg2m_does_not_import_langgraph():
    """The annotation layer is framework-free; importing lg2m must not drag in langgraph."""
    import subprocess
    import sys

    code = "import sys, lg2m; print('langgraph' in sys.modules or 'langchain_core' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False"
