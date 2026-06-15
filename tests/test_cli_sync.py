"""Layer 6 Task 7.1: the ``sync`` CLI command. docs/design.md Sections 11, 14.

CliRunner-driven exit-code and output checks. All paths are framework-free:
``run_sync`` never imports the user module, so the graph entry point can be a
non-importable stub.
"""

from __future__ import annotations

import textwrap

from typer.testing import CliRunner

from lg2m.cli import app
from lg2m.sync.lockfile import Lock, dumps_lock, set_base
from lg2m.sync.normalize import prose_hash

runner = CliRunner()

_CONFIG = textwrap.dedent(
    """\
    [tool.lg2m.graphs.g]
    graph = "pkg.nodes:build"
    markdown = "docs/contract.md"
    sys_path = ["src"]
    """
)


def _node_py(node_id: str, docstring: str | None = None) -> str:
    body = f'    """{docstring}"""\n' if docstring is not None else ""
    return (
        f"from lg2m import node\n\n"
        f'@node("{node_id}")\n'
        f"def {node_id}(state):\n"
        f"{body}    return state\n"
    )


def _md(node_id: str, prose: str) -> str:
    return textwrap.dedent(f"""\
        ---
        lg2m_graph: g
        ---
        ## Nodes
        ### `{node_id}`

        {prose}
    """)


def _project(tmp_path, *, node_id="n1", md_prose, node_docstring=None, lock_text=None):
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "nodes.py").write_text(_node_py(node_id, node_docstring), encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "contract.md").write_text(_md(node_id, md_prose), encoding="utf-8")
    if lock_text is not None:
        (tmp_path / ".lg2m.lock").write_text(lock_text, encoding="utf-8")
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(_CONFIG, encoding="utf-8")
    return cfg


# --- dry-run -----------------------------------------------------------------


def test_sync_dry_run_bootstrap_writes_nothing(tmp_path):
    cfg = _project(tmp_path, md_prose="The prose.", node_docstring=None)
    result = runner.invoke(app, ["sync", "-c", str(cfg), "--dry-run"])
    assert result.exit_code == 0, result.stdout
    assert "(dry run)" in result.stdout
    nodes_py = tmp_path / "src" / "pkg" / "nodes.py"
    assert '"""' not in nodes_py.read_text(encoding="utf-8")
    assert not (tmp_path / ".lg2m.lock").exists()


# --- bootstrap ---------------------------------------------------------------


def test_sync_bootstrap_writes_code_and_creates_lock(tmp_path):
    cfg = _project(tmp_path, md_prose="The prose.")
    result = runner.invoke(app, ["sync", "-c", str(cfg)])
    assert result.exit_code == 0, result.stdout
    assert "1 written" in result.stdout
    assert "code:     node:n1" in result.stdout
    assert "  lock:     updated" in result.stdout
    assert "The prose." in (tmp_path / "src" / "pkg" / "nodes.py").read_text(encoding="utf-8")
    assert (tmp_path / ".lg2m.lock").is_file()


# --- idempotency --------------------------------------------------------------


def test_sync_second_run_is_noop(tmp_path):
    cfg = _project(tmp_path, md_prose="The prose.")
    runner.invoke(app, ["sync", "-c", str(cfg)])
    lock_before = (tmp_path / ".lg2m.lock").read_bytes()
    result = runner.invoke(app, ["sync", "-c", str(cfg)])
    assert result.exit_code == 0
    assert "0 written" in result.stdout
    assert (tmp_path / ".lg2m.lock").read_bytes() == lock_before


# --- conflict -----------------------------------------------------------------


def _conflict_project(tmp_path):
    lock = Lock()
    set_base(lock, "g", "node", "n1", prose_hash("Original."))
    return _project(
        tmp_path,
        md_prose="Changed in Markdown.",
        node_docstring="Changed in code.",
        lock_text=dumps_lock(lock),
    )


def test_sync_conflict_exits_1(tmp_path):
    cfg = _conflict_project(tmp_path)
    result = runner.invoke(app, ["sync", "-c", str(cfg)])
    assert result.exit_code == 1
    assert "0 written" in result.stdout
    assert "1 unresolved" in result.stdout
    assert "conflict: node:n1" in result.output  # stderr via CliRunner .output


def test_sync_prefer_doc_resolves_conflict(tmp_path):
    cfg = _conflict_project(tmp_path)
    result = runner.invoke(app, ["sync", "-c", str(cfg), "--prefer", "doc"])
    assert result.exit_code == 0, result.output
    assert "0 unresolved" in result.stdout
    assert "Changed in Markdown." in (
        tmp_path / "src" / "pkg" / "nodes.py"
    ).read_text(encoding="utf-8")


def test_sync_prefer_code_resolves_conflict(tmp_path):
    cfg = _conflict_project(tmp_path)
    result = runner.invoke(app, ["sync", "-c", str(cfg), "--prefer", "code"])
    assert result.exit_code == 0, result.output
    assert "0 unresolved" in result.stdout
    assert "Changed in code." in (
        tmp_path / "docs" / "contract.md"
    ).read_text(encoding="utf-8")


# --- error paths --------------------------------------------------------------


def test_sync_bad_config_path_exits_2(tmp_path):
    result = runner.invoke(app, ["sync", "-c", str(tmp_path / "no_such.toml")])
    assert result.exit_code == 2


def test_sync_unknown_graph_id_exits_2(tmp_path):
    cfg = _project(tmp_path, md_prose="The prose.")
    result = runner.invoke(app, ["sync", "nonexistent", "-c", str(cfg)])
    assert result.exit_code == 2
