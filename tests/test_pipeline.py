"""Layer 3 Phase 5: the end-to-end check() pipeline against the REAL compiled graph."""

from __future__ import annotations

import subprocess
import sys

import pytest

from lg2m.diff.categories import DriftCategory
from lg2m.pipeline import check, validate


def _drop_example_modules():
    """Force a fresh import so check()'s loader repopulates the (reset) registry."""
    stale = [m for m in sys.modules if m == "support_pipeline" or m.startswith("support_pipeline.")]
    for name in stale:
        del sys.modules[name]


def test_importing_pipeline_pulls_in_no_framework():
    code = "import sys, lg2m.pipeline; assert 'langgraph' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_check_unknown_graph_id_is_error(golden_toml_path):
    report = check(golden_toml_path, "nope")
    assert not report.is_clean
    assert report.exit_code == 1


def test_check_import_failure_is_reported_not_raised(golden_md_text, tmp_path):
    """A bad graph entry yields a report with an IMPORT_FAILURE diagnostic (framework-free)."""
    md = tmp_path / "contract.md"
    md.write_text(golden_md_text, encoding="utf-8")
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.support_pipeline]\n"
        'graph = "no_such_module_zzz:build_graph"\n'
        f'markdown = "{md.name}"\n'
        "sys_path = []\n"
        "xray = true\n",
        encoding="utf-8",
    )
    report = check(cfg, "support_pipeline")
    assert DriftCategory.DIAGNOSTIC in {i.category for i in report.items}
    assert report.exit_code == 1


@pytest.mark.langgraph
def test_check_clean_oracle_end_to_end(golden_toml_path):
    """The milestone: all three sources, the REAL compiled graph, reconcile to empty."""
    _drop_example_modules()
    report = check(golden_toml_path, "support_pipeline")
    assert report.items == [], [f"{i.category.value}: {i.message}" for i in report.items]
    assert report.is_clean
    assert report.exit_code == 0


@pytest.mark.langgraph
def test_check_reports_node_drift(golden_md_text, golden_toml_path, tmp_path):
    src_root = str((golden_toml_path.parent / "src").resolve())
    md = tmp_path / "contract.md"
    md.write_text(golden_md_text.replace("compose_reply", "compose_final"), encoding="utf-8")
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.support_pipeline]\n"
        'graph = "support_pipeline.graph:build_graph"\n'
        f'markdown = "{md.name}"\n'
        f'sys_path = ["{src_root}"]\n'
        "xray = true\n",
        encoding="utf-8",
    )
    _drop_example_modules()
    report = check(cfg, "support_pipeline")
    cats = {i.category for i in report.items}
    assert DriftCategory.NODE_MISSING_IN_CODE in cats  # compose_final documented, not in code
    assert DriftCategory.NODE_MISSING_IN_DOC in cats  # compose_reply in code, not documented
    assert report.exit_code == 1


# --- validate() --------------------------------------------------------------


def test_validate_unknown_graph_id_is_error(golden_toml_path):
    report = validate(golden_toml_path, "nope")
    assert not report.is_clean
    assert report.exit_code == 1


def test_validate_missing_else_and_import_failure(golden_md_text, tmp_path):
    """Doc-side [else] scan + import-failure fold, framework-free (bogus graph module)."""
    md = tmp_path / "contract.md"
    md.write_text(
        golden_md_text.replace("investigate: [else]", "investigate: investigate_fallback"),
        encoding="utf-8",
    )
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.support_pipeline]\n"
        'graph = "no_such_module_zzz:build_graph"\n'
        f'markdown = "{md.name}"\n'
        "sys_path = []\n"
        "xray = true\n",
        encoding="utf-8",
    )
    report = validate(cfg, "support_pipeline")
    cats = {i.category for i in report.items}
    assert DriftCategory.MISSING_ELSE in cats  # the diagram fan-out lost its [else]
    assert DriftCategory.DIAGNOSTIC in cats  # the bogus entry point did not import
    assert report.exit_code == 1


def test_validate_missing_markdown_is_reported(tmp_path):
    """A markdown path that does not exist is reported, not raised (framework-free)."""
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.support_pipeline]\n"
        'graph = "no_such_module_zzz:build_graph"\n'
        'markdown = "absent.md"\n'
        "sys_path = []\n"
        "xray = true\n",
        encoding="utf-8",
    )
    report = validate(cfg, "support_pipeline")
    assert DriftCategory.DIAGNOSTIC in {i.category for i in report.items}
    assert report.exit_code == 1


def test_validate_requires_exactly_one_state_model(golden_md_text, tmp_path):
    """Import-success path: two @state_model classes -> STATE_MODEL_MISMATCH (framework-free)."""
    pkg = tmp_path / "dummy_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "graph.py").write_text(
        "from lg2m import state_model\n\n\n"
        "@state_model\n"
        "class StateA(dict):\n    pass\n\n\n"
        "@state_model\n"
        "class StateB(dict):\n    pass\n\n\n"
        "def build():\n    return object()\n",
        encoding="utf-8",
    )
    md = tmp_path / "contract.md"
    md.write_text(golden_md_text, encoding="utf-8")  # clean diagram: no MISSING_ELSE
    cfg = tmp_path / "lg2m.toml"
    cfg.write_text(
        "[tool.lg2m.graphs.dummy]\n"
        'graph = "dummy_pkg.graph:build"\n'
        f'markdown = "{md.name}"\n'
        f'sys_path = ["{tmp_path}"]\n'
        "xray = true\n",
        encoding="utf-8",
    )
    report = validate(cfg, "dummy")
    cats = {i.category for i in report.items}
    assert DriftCategory.STATE_MODEL_MISMATCH in cats
    assert DriftCategory.MISSING_ELSE not in cats  # the golden diagram keeps its [else]
    assert report.exit_code == 1


@pytest.mark.langgraph
def test_validate_clean_oracle(golden_toml_path):
    """The clean example validates: one @state_model, every fan-out has [else], import succeeds."""
    _drop_example_modules()
    report = validate(golden_toml_path, "support_pipeline")
    assert report.items == [], [f"{i.category.value}: {i.message}" for i in report.items]
    assert report.is_clean
    assert report.exit_code == 0
