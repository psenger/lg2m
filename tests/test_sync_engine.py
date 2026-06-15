"""Layer 6 Task 6.1: the sync engine (sync/engine.py::run_sync), framework-free."""

from __future__ import annotations

import textwrap

from lg2m.sync import run_sync
from lg2m.sync.lockfile import Lock, base_hash, dumps_lock, load_lock, set_base
from lg2m.sync.normalize import prose_hash

CONFIG = textwrap.dedent(
    """\
    [tool.lg2m.graphs.g]
    graph = "pkg.graph:build"
    markdown = "docs/contract.md"
    sys_path = ["src"]
    """
)


def _project(tmp_path, *, nodes_py, predicates_py, md, lock=None):
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "graph.py").write_text("def build():\n    return None\n", encoding="utf-8")
    (pkg / "nodes.py").write_text(nodes_py, encoding="utf-8")
    (pkg / "predicates.py").write_text(predicates_py, encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "contract.md").write_text(md, encoding="utf-8")
    config = tmp_path / "lg2m.toml"
    config.write_text(CONFIG, encoding="utf-8")
    if lock is not None:
        (tmp_path / ".lg2m.lock").write_text(lock, encoding="utf-8")
    return config


def _md(*, nodes, predicates):
    parts = ["---", "lg2m_graph: g", "---", "", "## Nodes", ""]
    for nid, prose in nodes.items():
        parts += [f"### `{nid}`", "", prose, ""]
    parts += ["## Predicates", ""]
    for pid, prose in predicates.items():
        parts += [f"### `{pid}`", "", prose, ""]
    return "\n".join(parts) + "\n"


def _node(key, doc=None):
    body = f'    """{doc}"""\n' if doc is not None else ""
    return (
        f'from lg2m import node\n@node("{key}")\n'
        f'def {key}(state):\n{body}    return state\n'
    )


def _pred(key, doc=None):
    body = f'    """{doc}"""\n' if doc is not None else ""
    return (
        f'from lg2m import predicate\n@predicate("{key}")\n'
        f'def {key}(state):\n{body}    return True\n'
    )


def test_bootstrap_writes_docstring_from_markdown(tmp_path):
    """No lock, code docstring empty, Markdown has prose -> WRITE_CODE (md -> docstring)."""
    config = _project(
        tmp_path,
        nodes_py=_node("n1"),
        predicates_py=_pred("p1"),
        md=_md(nodes={"n1": "Node one prose."}, predicates={"p1": "Pred one prose."}),
    )
    result = run_sync(config, "g")
    assert result.exit_code == 0
    assert ("node", "n1") in result.code_written
    assert ("predicate", "p1") in result.code_written
    assert "Node one prose." in (tmp_path / "src" / "pkg" / "nodes.py").read_text()
    lock = load_lock(tmp_path / ".lg2m.lock")
    assert base_hash(lock, "g", "node", "n1") == prose_hash("Node one prose.")


def test_only_code_changed_writes_markdown(tmp_path):
    """Base present, only the docstring moved -> WRITE_MD (docstring -> md)."""
    lk = Lock()
    set_base(lk, "g", "node", "n1", prose_hash("Original prose."))
    config = _project(
        tmp_path,
        nodes_py=_node("n1", "Changed in code."),
        predicates_py="from lg2m import predicate\n",
        md=_md(nodes={"n1": "Original prose."}, predicates={}),
        lock=dumps_lock(lk),
    )
    result = run_sync(config, "g")
    assert result.exit_code == 0
    assert ("node", "n1") in result.md_written
    md_out = (tmp_path / "docs" / "contract.md").read_text()
    assert "Changed in code." in md_out
    assert "Original prose." not in md_out


def test_conflict_writes_nothing_and_is_reported(tmp_path):
    """No base, both sides non-empty and differ -> CONFLICT; nothing written, exit 1."""
    config = _project(
        tmp_path,
        nodes_py=_node("n1", "Code version."),
        predicates_py="from lg2m import predicate\n",
        md=_md(nodes={"n1": "Doc version."}, predicates={}),
    )
    nodes_before = (tmp_path / "src" / "pkg" / "nodes.py").read_text()
    md_before = (tmp_path / "docs" / "contract.md").read_text()
    result = run_sync(config, "g")
    assert result.exit_code == 1
    assert ("node", "n1") in result.conflicts
    assert (tmp_path / "src" / "pkg" / "nodes.py").read_text() == nodes_before
    assert (tmp_path / "docs" / "contract.md").read_text() == md_before
    assert not (tmp_path / ".lg2m.lock").exists()


def test_prefer_doc_resolves_conflict(tmp_path):
    """--prefer doc resolves a conflict by writing the docstring from the Markdown."""
    config = _project(
        tmp_path,
        nodes_py=_node("n1", "Code version."),
        predicates_py="from lg2m import predicate\n",
        md=_md(nodes={"n1": "Doc wins."}, predicates={}),
    )
    result = run_sync(config, "g", prefer="doc")
    assert result.exit_code == 0
    assert ("node", "n1") in result.code_written
    assert "Doc wins." in (tmp_path / "src" / "pkg" / "nodes.py").read_text()


def test_second_run_is_noop_and_lock_byte_stable(tmp_path):
    """After convergence, a second sync writes nothing and leaves .lg2m.lock byte-stable."""
    config = _project(
        tmp_path,
        nodes_py=_node("n1"),
        predicates_py=_pred("p1"),
        md=_md(nodes={"n1": "Node prose."}, predicates={"p1": "Pred prose."}),
    )
    run_sync(config, "g")
    lock1 = (tmp_path / ".lg2m.lock").read_text()
    nodes1 = (tmp_path / "src" / "pkg" / "nodes.py").read_text()
    md1 = (tmp_path / "docs" / "contract.md").read_text()

    result2 = run_sync(config, "g")
    assert result2.wrote_files is False
    assert result2.lock_written is False
    assert (tmp_path / ".lg2m.lock").read_text() == lock1
    assert (tmp_path / "src" / "pkg" / "nodes.py").read_text() == nodes1
    assert (tmp_path / "docs" / "contract.md").read_text() == md1


def test_raw_prefixed_docstring_is_skipped_and_reported(tmp_path):
    """A WRITE_CODE that targets a raw/byte-prefixed docstring is refused, not corrupted."""
    raw_doc = "Raw \\d code prose."
    lk = Lock()
    set_base(lk, "g", "node", "n1", prose_hash(raw_doc))  # base == code, so only md "changed"
    config = _project(
        tmp_path,
        nodes_py=(
            'from lg2m import node\n@node("n1")\n'
            'def n1(state):\n    r"""Raw \\d code prose."""\n    return state\n'
        ),
        predicates_py="from lg2m import predicate\n",
        md=_md(nodes={"n1": "Doc prose changed."}, predicates={}),
        lock=dumps_lock(lk),
    )
    before = (tmp_path / "src" / "pkg" / "nodes.py").read_text()
    result = run_sync(config, "g")
    assert ("node", "n1") in result.raw_prefix_skips
    assert result.exit_code == 1
    assert (tmp_path / "src" / "pkg" / "nodes.py").read_text() == before


def test_interleaved_markdown_is_skipped_and_reported(tmp_path):
    """A WRITE_MD into an interleaved (prose-after-meta) entity is refused, not guessed."""
    from lg2m.parsing.markdown import parse_markdown

    md = (
        "---\nlg2m_graph: g\n---\n\n"
        "## Nodes\n\n"
        "### `n1`\n\n"
        "Leading prose.\n\n"
        "| meta | value |\n\n"
        "Trailing prose.\n\n"
        "## Predicates\n\n"
    )
    entity_prose = parse_markdown(md).entity("n1").prose
    lk = Lock()
    set_base(lk, "g", "node", "n1", prose_hash(entity_prose))  # base == md, so only code "changed"
    config = _project(
        tmp_path,
        nodes_py=_node("n1", "Changed docstring."),
        predicates_py="from lg2m import predicate\n",
        md=md,
        lock=dumps_lock(lk),
    )
    before = (tmp_path / "docs" / "contract.md").read_text()
    result = run_sync(config, "g")
    assert ("node", "n1") in result.interleaved_skips
    assert result.exit_code == 1
    assert (tmp_path / "docs" / "contract.md").read_text() == before


def test_unresolvable_package_is_a_clean_noop(tmp_path):
    """When the package dir can't be located (no import attempted), sync is a clean no-op."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "contract.md").write_text(
        _md(nodes={"n1": "x"}, predicates={}), encoding="utf-8"
    )
    (tmp_path / "lg2m.toml").write_text(
        textwrap.dedent(
            """\
            [tool.lg2m.graphs.g]
            graph = "ghost.mod:build"
            markdown = "docs/contract.md"
            sys_path = ["src"]
            """
        ),
        encoding="utf-8",
    )
    result = run_sync(tmp_path / "lg2m.toml", "g")
    assert result.exit_code == 0
    assert result.wrote_files is False


def test_dry_run_writes_nothing(tmp_path):
    """--dry-run reports planned writes but touches no file and creates no lock."""
    config = _project(
        tmp_path,
        nodes_py=_node("n1"),
        predicates_py="from lg2m import predicate\n",
        md=_md(nodes={"n1": "Node prose."}, predicates={}),
    )
    nodes_before = (tmp_path / "src" / "pkg" / "nodes.py").read_text()
    result = run_sync(config, "g", dry_run=True)
    assert ("node", "n1") in result.code_written  # planned
    assert (tmp_path / "src" / "pkg" / "nodes.py").read_text() == nodes_before
    assert not (tmp_path / ".lg2m.lock").exists()
