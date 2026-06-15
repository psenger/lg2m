"""Shared pytest fixtures for the lg2m foundation suite.

Adds ``src/`` to ``sys.path`` so the suite runs without an editable install,
and exposes the golden ``support_pipeline`` fixture paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

GOLDEN_DIR = REPO_ROOT / "examples" / "support_pipeline"
GOLDEN_MD = GOLDEN_DIR / "docs" / "support_pipeline.md"
GOLDEN_TOML = GOLDEN_DIR / "lg2m.toml"
GOLDEN_SRC = GOLDEN_DIR / "src" / "support_pipeline"
GOLDEN_SRC_ROOT = GOLDEN_DIR / "src"

# A minimal, subgraph-free contract used by the scaffold/gen golden round-trips.
MINI_MD = REPO_ROOT / "tests" / "fixtures" / "mini_pipeline.md"


@pytest.fixture
def mini_md_text() -> str:
    return MINI_MD.read_text(encoding="utf-8")


@pytest.fixture
def golden_md_path() -> Path:
    return GOLDEN_MD


@pytest.fixture
def golden_md_text() -> str:
    return GOLDEN_MD.read_text(encoding="utf-8")


@pytest.fixture
def golden_toml_path() -> Path:
    return GOLDEN_TOML


@pytest.fixture
def golden_src_dir() -> Path:
    """The annotated example source, read with the AST reader (no import)."""
    return GOLDEN_SRC


@pytest.fixture
def golden_compiled():
    """Compile the real lg2m-annotated support_pipeline graph.

    Importing the package imports langgraph, so any test using this fixture must be
    marked ``@pytest.mark.langgraph``. The import also populates the global registry
    (the decorators run); the autouse ``reset_registry`` clears it afterwards.
    """
    root = str(GOLDEN_SRC_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    from support_pipeline.graph import build_graph

    return build_graph()


@pytest.fixture(autouse=True)
def reset_registry():
    """Isolate the per-import annotation registry between tests.

    The registry is a module-level singleton, so without this an annotation
    registered in one test would leak into the next.
    """
    from lg2m.annotations import registry

    registry.reset()
    yield
    registry.reset()
