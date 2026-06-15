"""Layer 6 Task 7.2: end-to-end sync on a copy of examples/support_pipeline/.

Exercises ``run_sync()`` directly (no CLI layer) on a realistic multi-file
package. Framework-free: the sync engine never imports the user module.

The support_pipeline example has one pre-existing docstring conflict
(``escalate_to_human`` has a docstring in code that differs from the MD prose).
All tests use ``prefer="doc"`` for the first sync to resolve that conflict and
bootstrap all other entities.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lg2m.sync import run_sync
from lg2m.sync.normalize import normalize_prose

EXAMPLE = Path(__file__).parent.parent / "examples" / "support_pipeline"


def _ignore(directory, names):
    return [n for n in names if n in ("__pycache__", ".DS_Store")]


@pytest.fixture
def sp(tmp_path):
    """Copy support_pipeline into tmp_path; return its root."""
    shutil.copytree(EXAMPLE, tmp_path / "sp", ignore=_ignore)
    return tmp_path / "sp"


def _config(sp: Path) -> Path:
    return sp / "lg2m.toml"


def _nodes_py(sp: Path) -> Path:
    return sp / "src" / "support_pipeline" / "nodes.py"


def _md(sp: Path) -> Path:
    return sp / "docs" / "support_pipeline.md"


# --- bootstrap ----------------------------------------------------------------


def test_sync_e2e_bootstrap_writes_docstrings(sp):
    """First sync bootstraps docstrings from Markdown prose; resolves the
    escalate_to_human conflict via --prefer doc."""
    result = run_sync(_config(sp), "support_pipeline", prefer="doc")
    assert result.exit_code == 0
    assert len(result.code_written) >= 10  # many nodes + predicates bootstrapped
    assert result.conflicts == []
    assert result.lock_written
    nodes_text = _nodes_py(sp).read_text(encoding="utf-8")
    assert "Entry node." in nodes_text   # ingest_ticket MD prose written to code


# --- idempotency --------------------------------------------------------------


def test_sync_e2e_second_run_is_noop(sp):
    """After bootstrap, a second run writes nothing and leaves the lock unchanged."""
    run_sync(_config(sp), "support_pipeline", prefer="doc")
    lock_before = (sp / ".lg2m.lock").read_bytes()
    result = run_sync(_config(sp), "support_pipeline")
    assert result.exit_code == 0
    assert not result.wrote_files
    assert (sp / ".lg2m.lock").read_bytes() == lock_before


# --- MD drift → code updated -------------------------------------------------


def test_sync_e2e_md_drift_updates_code(sp):
    """Drift MD prose for a node after bootstrap; sync writes updated docstring."""
    run_sync(_config(sp), "support_pipeline", prefer="doc")

    md_path = _md(sp)
    md_text = md_path.read_text(encoding="utf-8")
    new_md = md_text.replace(
        "Entry node. Normalizes the",
        "DRIFTED: Entry node. Normalizes the",
        1,
    )
    assert new_md != md_text, "test setup: replacement didn't match"
    md_path.write_text(new_md, encoding="utf-8")

    result = run_sync(_config(sp), "support_pipeline")
    assert result.exit_code == 0
    assert ("node", "ingest_ticket") in result.code_written
    assert "DRIFTED:" in _nodes_py(sp).read_text(encoding="utf-8")


# --- code drift → MD updated -------------------------------------------------


def test_sync_e2e_code_drift_updates_md(sp):
    """Drift a code docstring after bootstrap; sync writes updated MD prose."""
    run_sync(_config(sp), "support_pipeline", prefer="doc")

    # fetch_history got its docstring from MD prose during bootstrap.
    # Mutate the docstring in code to trigger WRITE_MD on the next sync.
    nodes_path = _nodes_py(sp)
    nodes_text = nodes_path.read_text(encoding="utf-8")
    fetch_prose = normalize_prose(
        "Parallel branch A. Writes the shared `enrichment` channel (prior-ticket history)."
    )
    assert fetch_prose in normalize_prose(nodes_text), \
        "test setup: expected fetch_history docstring not found after bootstrap"
    new_nodes = nodes_text.replace(
        "Parallel branch A. Writes the shared `enrichment` channel (prior-ticket history).",
        "CODE DRIFTED: Parallel branch A writes prior-ticket history.",
        1,
    )
    assert new_nodes != nodes_text, "test setup: replacement didn't match"
    nodes_path.write_text(new_nodes, encoding="utf-8")

    result = run_sync(_config(sp), "support_pipeline")
    assert result.exit_code == 0
    assert ("node", "fetch_history") in result.md_written
    assert "CODE DRIFTED:" in _md(sp).read_text(encoding="utf-8")
