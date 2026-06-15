"""AC-01 / AC-02 / AC-03: the config loader reads [tool.lg2m.graphs.*]."""

from __future__ import annotations

from pathlib import Path

from lg2m.config import loader

REPO_ROOT = Path(__file__).resolve().parents[1]

PYPROJECT_BLOCK = """\
[tool.lg2m.graphs.support_pipeline]
graph = "support_pipeline.graph:build_graph"
markdown = "docs/support_pipeline.md"
sys_path = ["src"]
xray = true
"""


def test_load_standalone_toml(golden_toml_path):
    """AC-02: the standalone lg2m.toml yields the support_pipeline entry."""
    graphs = loader.load(golden_toml_path)
    assert set(graphs) == {"support_pipeline"}
    cfg = graphs["support_pipeline"]
    assert cfg["graph"] == "support_pipeline.graph:build_graph"
    assert cfg["markdown"] == "docs/support_pipeline.md"
    assert cfg["sys_path"] == ["src"]
    assert cfg["xray"] is True


def test_pyproject_and_standalone_are_identical(golden_toml_path, tmp_path):
    """AC-01 + AC-02: a pyproject [tool.lg2m] section equals the standalone file."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\nversion = "0.0.0"\n\n' + PYPROJECT_BLOCK,
        encoding="utf-8",
    )
    assert loader.load(pyproject) == loader.load(golden_toml_path)


def test_values_keep_their_toml_types(golden_toml_path):
    cfg = loader.load(golden_toml_path)["support_pipeline"]
    assert isinstance(cfg["xray"], bool)
    assert isinstance(cfg["sys_path"], list)


def test_missing_section_returns_empty(tmp_path):
    f = tmp_path / "pyproject.toml"
    f.write_text('[project]\nname = "demo"\nversion = "0.0.0"\n', encoding="utf-8")
    assert loader.load(f) == {}


def test_returned_entries_are_isolated_copies(golden_toml_path):
    a = loader.load(golden_toml_path)
    a["support_pipeline"]["xray"] = False
    b = loader.load(golden_toml_path)
    assert b["support_pipeline"]["xray"] is True


def test_toml_shim_parses(tmp_path):
    """AC-03 (runtime side): the resolved tomllib/tomli shim reads binary TOML."""
    f = tmp_path / "x.toml"
    f.write_text("[tool.lg2m.graphs.g]\ngraph = \"m:f\"\n", encoding="utf-8")
    with f.open("rb") as fh:
        parsed = loader.tomllib.load(fh)
    assert parsed["tool"]["lg2m"]["graphs"]["g"]["graph"] == "m:f"


def test_pyproject_declares_tomli_backport():
    """AC-03 (provisioning side): 3.10 gets tomli via a conditional dependency."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "tomli >= 2.0 ; python_version < '3.11'" in text
