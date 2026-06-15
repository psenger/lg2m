"""Layer 3 Phase 4: config -> ResolvedGraph (framework-free)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lg2m.config import loader
from lg2m.discovery.resolve import ConfigError, resolve


def test_resolve_real_config(golden_toml_path):
    graphs = loader.load(golden_toml_path)
    r = resolve(
        graphs["support_pipeline"], base_dir=golden_toml_path.parent, graph_id="support_pipeline"
    )
    assert r.module == "support_pipeline.graph"
    assert r.attr == "build_graph"
    assert r.markdown_path.is_absolute() and r.markdown_path.name == "support_pipeline.md"
    assert r.sys_paths and r.sys_paths[0].is_absolute() and r.sys_paths[0].name == "src"
    assert r.xray is True
    assert r.framework == "langgraph"


def test_resolve_missing_graph_raises():
    with pytest.raises(ConfigError):
        resolve({"markdown": "x.md"}, base_dir=Path("/tmp"), graph_id="g")


def test_resolve_missing_markdown_raises():
    with pytest.raises(ConfigError):
        resolve({"graph": "m:f"}, base_dir=Path("/tmp"), graph_id="g")


def test_resolve_bad_graph_format_raises():
    with pytest.raises(ConfigError):
        resolve({"graph": "no_colon", "markdown": "x.md"}, base_dir=Path("/tmp"), graph_id="g")
