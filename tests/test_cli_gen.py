"""Layer 5 / Phase 3: the ``gen`` CLI command (docs/design.md Sections 10, 11, 14).

CliRunner-driven exit-code checks. ``--from-doc`` never loads the graph, so most paths are
framework-free; the ``--from-code`` success paths introspect the real example and are gated
``@pytest.mark.langgraph``. Every path writes only where asked.
"""

from __future__ import annotations

import sys

import pytest
from typer.testing import CliRunner

from lg2m.cli import app

runner = CliRunner()


def _drop_example_modules() -> None:
    stale = [m for m in sys.modules if m == "support_pipeline" or m.startswith("support_pipeline.")]
    for name in stale:
        del sys.modules[name]


def _mini_config(tmp_path, mini_md_text):
    md = tmp_path / "mini.md"
    md.write_text(mini_md_text, encoding="utf-8")
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.mini]\n"
        'graph = "mini_pkg.graph:build_graph"\n'
        f'markdown = "{md.name}"\n'
        "sys_path = []\n"
        "xray = true\n",
        encoding="utf-8",
    )
    return cfg


# --- direction selection (exit 2) --------------------------------------------


def test_gen_requires_exactly_one_direction(tmp_path, mini_md_text):
    cfg = _mini_config(tmp_path, mini_md_text)
    assert runner.invoke(app, ["gen", "-c", str(cfg)]).exit_code == 2  # neither
    both = runner.invoke(app, ["gen", "--from-doc", "--from-code", "-c", str(cfg)])
    assert both.exit_code == 2


# --- --from-doc (framework-free) ---------------------------------------------


def test_gen_from_doc_to_stdout_writes_nothing(tmp_path, mini_md_text):
    cfg = _mini_config(tmp_path, mini_md_text)
    result = runner.invoke(app, ["gen", "--from-doc", "-c", str(cfg)])
    assert result.exit_code == 0, result.stdout
    assert "def build_graph():" in result.stdout
    assert '@node("ingest")' in result.stdout
    assert "# ===== state.py =====" in result.stdout
    # dry run leaves only the inputs
    assert {p.name for p in tmp_path.iterdir()} == {"mini.md", "lg2m.toml"}


def test_gen_from_doc_writes_and_refuses_overwrite(tmp_path, mini_md_text):
    cfg = _mini_config(tmp_path, mini_md_text)
    out = tmp_path / "pkg"
    first = runner.invoke(app, ["gen", "--from-doc", "-c", str(cfg), "--out", str(out)])
    assert first.exit_code == 0, first.stdout
    assert (out / "graph.py").is_file() and (out / "state.py").is_file()

    second = runner.invoke(app, ["gen", "--from-doc", "-c", str(cfg), "--out", str(out)])
    assert second.exit_code == 2  # refuses to overwrite


def test_gen_from_doc_langchain_is_rejected(tmp_path, mini_md_text):
    cfg = _mini_config(tmp_path, mini_md_text)
    result = runner.invoke(app, ["gen", "--from-doc", "-c", str(cfg), "--framework", "langchain"])
    assert result.exit_code == 2


def test_gen_from_doc_unknown_model_style_is_rejected(tmp_path, mini_md_text):
    cfg = _mini_config(tmp_path, mini_md_text)
    result = runner.invoke(app, ["gen", "--from-doc", "-c", str(cfg), "--model-style", "dataclass"])
    assert result.exit_code == 2


# --- --from-code load failure (framework-free: import fails before the adapter) ----


def test_gen_from_code_import_failure_exits_1(tmp_path, mini_md_text):
    md = tmp_path / "mini.md"
    md.write_text(mini_md_text, encoding="utf-8")
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.only]\n"
        'graph = "no_such_module_zzz:build_graph"\n'
        f'markdown = "{md.name}"\n'
        "sys_path = []\n"
        "xray = true\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["gen", "--from-code", "-c", str(cfg)])
    assert result.exit_code == 1


# --- --from-code success (framework) -----------------------------------------


def _from_code_args(golden_toml_path, *extra):
    return ["gen", "--from-code", "support_pipeline", "-c", str(golden_toml_path), *extra]


@pytest.mark.langgraph
def test_gen_from_code_to_stdout(golden_toml_path):
    _drop_example_modules()
    result = runner.invoke(app, _from_code_args(golden_toml_path))
    assert result.exit_code == 0, result.stdout
    assert "lg2m_graph: support_pipeline" in result.stdout
    assert "## Graph" in result.stdout and "## Edges" in result.stdout


@pytest.mark.langgraph
def test_gen_from_code_writes_file(golden_toml_path, tmp_path):
    _drop_example_modules()
    out = tmp_path / "contract.md"
    result = runner.invoke(app, _from_code_args(golden_toml_path, "--out", str(out)))
    assert result.exit_code == 0, result.stdout
    assert out.is_file()
    assert "## Graph" in out.read_text(encoding="utf-8")


@pytest.mark.langgraph
def test_gen_from_code_refuses_overwrite(golden_toml_path, tmp_path):
    _drop_example_modules()
    out = tmp_path / "contract.md"
    out.write_text("existing", encoding="utf-8")
    result = runner.invoke(app, _from_code_args(golden_toml_path, "--out", str(out)))
    assert result.exit_code == 2
    assert out.read_text(encoding="utf-8") == "existing"  # untouched
