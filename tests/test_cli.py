"""Layer 4: the Typer CLI (exit-code contract + each command). docs/design.md Sections 11, 14.

CliRunner-driven. Tests that run the real compiled graph are gated ``@pytest.mark.langgraph``;
the rest are framework-free (they never import langgraph).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from lg2m.cli import OutputFormat, _emit, _resolve_graph_id, app
from lg2m.config import loader as config_loader
from lg2m.diff.categories import DriftCategory, Severity
from lg2m.report.model import DriftItem, DriftReport

runner = CliRunner()


def _drop_example_modules() -> None:
    """Force a fresh import so the loader repopulates the (reset) registry."""
    stale = [m for m in sys.modules if m == "support_pipeline" or m.startswith("support_pipeline.")]
    for name in stale:
        del sys.modules[name]


def _write_bogus_single_graph(tmp_path, golden_md_text) -> Path:
    """A config with exactly one graph whose entry point fails to import (framework-free)."""
    md = tmp_path / "contract.md"
    md.write_text(golden_md_text, encoding="utf-8")
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.only]\n"
        'graph = "no_such_module_zzz:build_graph"\n'
        f'markdown = "{md.name}"\n'
        "sys_path = []\n"
        "xray = true\n",
        encoding="utf-8",
    )
    return cfg


# --- list --------------------------------------------------------------------


def test_list_text(golden_toml_path):
    result = runner.invoke(app, ["list", "-c", str(golden_toml_path)])
    assert result.exit_code == 0
    assert "support_pipeline" in result.stdout


def test_list_json(golden_toml_path):
    result = runner.invoke(app, ["list", "-c", str(golden_toml_path), "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "support_pipeline" in payload
    assert payload["support_pipeline"]["graph"] == "support_pipeline.graph:build_graph"


# --- usage / config errors (exit 2) ------------------------------------------


def test_check_unknown_graph_id_exits_2(golden_toml_path):
    result = runner.invoke(app, ["check", "nope", "-c", str(golden_toml_path)])
    assert result.exit_code == 2


def test_missing_config_file_exits_2(tmp_path):
    result = runner.invoke(app, ["list", "-c", str(tmp_path / "absent.toml")])
    assert result.exit_code == 2


def test_malformed_toml_exits_2(tmp_path):
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text("this is = = not valid toml ===\n", encoding="utf-8")
    result = runner.invoke(app, ["list", "-c", str(cfg)])
    assert result.exit_code == 2


def test_no_config_discovered_exits_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # empty dir: no lg2m.toml or pyproject.toml
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 2


def test_check_config_error_exits_2(tmp_path):
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        '[tool.lg2m.graphs.bad]\ngraph = "no_colon_here"\nmarkdown = "d.md"\n', encoding="utf-8"
    )
    assert runner.invoke(app, ["check", "-c", str(cfg)]).exit_code == 2  # resolve() -> ConfigError
    assert runner.invoke(app, ["validate", "-c", str(cfg)]).exit_code == 2


def test_list_empty_config(tmp_path):
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text("[tool.lg2m]\n", encoding="utf-8")  # no graphs table
    result = runner.invoke(app, ["list", "-c", str(cfg)])
    assert result.exit_code == 0
    assert "no graphs configured" in result.stdout


def test_bad_format_value_exits_2(golden_toml_path):
    result = runner.invoke(app, ["list", "-c", str(golden_toml_path), "--format", "yaml"])
    assert result.exit_code == 2


# --- config auto-discovery ---------------------------------------------------


def test_auto_discover_lg2m_toml(tmp_path, monkeypatch):
    (tmp_path / "lg2m.toml").write_text(
        '[tool.lg2m.graphs.g1]\ngraph = "m:f"\nmarkdown = "d.md"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "g1" in result.stdout


def test_auto_discover_pyproject_fallback(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.lg2m.graphs.g2]\ngraph = "m:f"\nmarkdown = "d.md"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "g2" in result.stdout


# --- init --------------------------------------------------------------------


def test_init_writes_and_refuses_overwrite(tmp_path):
    target = tmp_path / "nested" / "lg2m.toml"
    result = runner.invoke(app, ["init", "-c", str(target)])
    assert result.exit_code == 0
    assert target.is_file()
    # the template is a valid lg2m config
    assert "my_graph" in config_loader.load(target)
    # second run refuses to overwrite
    again = runner.invoke(app, ["init", "-c", str(target)])
    assert again.exit_code == 2


# --- validate (framework-free paths) -----------------------------------------


def test_validate_default_graph_id_when_single(tmp_path, golden_md_text):
    """Omitting GRAPH_ID resolves the sole graph (exit 1 from import failure, not exit 2)."""
    cfg = _write_bogus_single_graph(tmp_path, golden_md_text)
    result = runner.invoke(app, ["validate", "-c", str(cfg)])
    assert result.exit_code == 1


def test_validate_json_output_parses(tmp_path, golden_md_text):
    cfg = _write_bogus_single_graph(tmp_path, golden_md_text)
    result = runner.invoke(app, ["validate", "-c", str(cfg), "--format", "json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 1
    assert payload["items"]


# --- helper unit tests (cover the resolution/emit branches) ------------------


def test_resolve_graph_id_empty_and_ambiguous():
    with pytest.raises(typer.Exit) as none_configured:
        _resolve_graph_id({}, None)
    assert none_configured.value.exit_code == 2
    with pytest.raises(typer.Exit) as ambiguous:
        _resolve_graph_id({"a": {}, "b": {}}, None)
    assert ambiguous.value.exit_code == 2


def test_emit_no_prose_filters(capsys):
    report = DriftReport(graph_id="g")
    report.add(DriftItem(DriftCategory.PROSE_DRIFT, Severity.WARNING, "n1", "prose differs"))
    report.add(DriftItem(DriftCategory.NODE_MISSING_IN_DOC, Severity.ERROR, "n2", "missing"))
    _emit(report, OutputFormat.text, no_prose=True)
    out = capsys.readouterr().out
    assert "prose differs" not in out
    assert "n2" in out
    assert all(i.category is not DriftCategory.PROSE_DRIFT for i in report.items)


# --- end-to-end against the real compiled graph ------------------------------


@pytest.mark.langgraph
def test_check_clean_oracle_cli(golden_toml_path):
    _drop_example_modules()
    result = runner.invoke(app, ["check", "support_pipeline", "-c", str(golden_toml_path)])
    assert result.exit_code == 0, result.stdout
    assert "clean" in result.stdout


@pytest.mark.langgraph
def test_check_writes_nothing(golden_toml_path, tmp_path, monkeypatch):
    """A check run must not write to the working directory (docs/design.md Section 14)."""
    monkeypatch.chdir(tmp_path)
    _drop_example_modules()
    result = runner.invoke(app, ["check", "support_pipeline", "-c", str(golden_toml_path)])
    assert result.exit_code == 0, result.stdout
    assert list(tmp_path.iterdir()) == []
