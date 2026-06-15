"""Layer 5 / Phase 1: ``gen --from-doc`` code generation (docs/design.md Sections 10, 14).

Framework-free unit tests over ``scaffold.generate_code`` (every emitted file parses; the router
mapping, node/predicate stubs, reducers, and option errors are correct), plus the
``@pytest.mark.langgraph`` golden: markdown -> generated code -> compile + introspect -> IR equals
the doc-side IR (the minimal subgraph-free fixture; see the spec's scope refinement).
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from _roundtrip import introspect_generated, structural_key
from lg2m.annotations import reader
from lg2m.diff.assemble import assemble_doc_model
from lg2m.ir import Attribute, DataModel, Edge, GraphModel, Node, NodeKind
from lg2m.parsing.markdown import parse_markdown
from lg2m.scaffold import GENERATED_FILES, ScaffoldError, generate_code

REPO_ROOT = Path(__file__).resolve().parent.parent


def _doc_model(text: str) -> GraphModel:
    name = "mini_pipeline.md"
    return assemble_doc_model(parse_markdown(text, file=name), file=name)


# --- framework-free unit tests -----------------------------------------------


def test_every_generated_file_parses(mini_md_text):
    files = generate_code(_doc_model(mini_md_text))
    assert set(files) == set(GENERATED_FILES)
    for src in files.values():
        ast.parse(src)  # raises SyntaxError on malformed output
        assert src.endswith("\n")


def test_router_mapping_matches_the_contract(mini_md_text, tmp_path):
    model = _doc_model(mini_md_text)
    files = generate_code(model)
    routing = tmp_path / "routing.py"
    routing.write_text(files["routing.py"], encoding="utf-8")

    recovered = {
        r.source_id: (r.branches, r.else_target) for r in reader.read_file(routing).routers
    }
    expected = {s: (r.branches, r.else_target) for s, r in model.routes.items()}
    assert recovered == expected
    assert recovered["classify"] == (
        (("is_fast", "fast_path"), ("is_slow", "slow_path")), "fallback",
    )


def test_node_and_predicate_stubs(mini_md_text, tmp_path):
    model = _doc_model(mini_md_text)
    files = generate_code(model)

    (tmp_path / "nodes.py").write_text(files["nodes.py"], encoding="utf-8")
    (tmp_path / "predicates.py").write_text(files["predicates.py"], encoding="utf-8")
    node_anns = reader.read_file(tmp_path / "nodes.py").annotations
    pred_anns = reader.read_file(tmp_path / "predicates.py").annotations
    node_keys = {r.key for r in node_anns if r.kind == "node"}
    pred_keys = {r.key for r in pred_anns if r.kind == "predicate"}

    expected_nodes = {n.id for n in model.nodes.values() if n.kind is NodeKind.NODE}
    assert node_keys == expected_nodes
    assert pred_keys == {"is_fast", "is_slow"}
    # sentinels never become node stubs
    assert "__start__" not in node_keys and "__end__" not in node_keys


def test_reducer_attributes_are_wrapped(mini_md_text):
    state = generate_code(_doc_model(mini_md_text))["state.py"]
    assert "messages: Annotated[list, add_messages]" in state
    assert "attempts: Annotated[int, operator.add]" in state
    assert "flags: dict" in state  # plain field, no Annotated
    assert "from langgraph.graph.message import add_messages" in state
    assert "import operator" in state


def test_typeddict_is_default_style(mini_md_text):
    state = generate_code(_doc_model(mini_md_text))["state.py"]
    assert "class MiniState(TypedDict):" in state
    assert "from typing import Annotated, TypedDict" in state
    assert "pydantic" not in state


def test_pydantic_model_style(mini_md_text):
    state = generate_code(_doc_model(mini_md_text), model_style="pydantic")["state.py"]
    assert "class MiniState(BaseModel):" in state
    assert "from pydantic import BaseModel" in state
    ast.parse(state)


def test_custom_reducer_emits_an_importable_stub():
    gm = GraphModel(graph_id="x", origin="markdown")
    gm.nodes["__start__"] = Node("__start__", kind=NodeKind.START)
    gm.nodes["__end__"] = Node("__end__", kind=NodeKind.END)
    gm.nodes["a"] = Node("a")
    gm.edges = [Edge("__start__", "a"), Edge("a", "__end__")]
    gm.models["S"] = DataModel(
        name="S", style="", is_graph_state=True,
        attributes=(Attribute("log", "list", "extend_unique"),),
    )
    gm.state_model_name = "S"

    state = generate_code(gm)["state.py"]
    assert "def extend_unique(left, right):" in state
    assert "log: Annotated[list, extend_unique]" in state
    ast.parse(state)


def test_langchain_framework_is_rejected(mini_md_text):
    with pytest.raises(ScaffoldError, match="langchain"):
        generate_code(_doc_model(mini_md_text), framework="langchain")


def test_unknown_model_style_is_rejected(mini_md_text):
    with pytest.raises(ScaffoldError, match="model-style"):
        generate_code(_doc_model(mini_md_text), model_style="dataclass")


def test_contract_without_state_model_is_rejected():
    gm = GraphModel(graph_id="x", origin="markdown")
    gm.nodes["a"] = Node("a")
    with pytest.raises(ScaffoldError, match="state_model"):
        generate_code(gm)


def test_generate_code_on_full_example_parses(golden_md_text):
    """Lenient smoke: the rich example (subgraph / Send / Command) still emits parseable code."""
    model = assemble_doc_model(parse_markdown(golden_md_text, file="ex.md"), file="ex.md")
    files = generate_code(model)
    for src in files.values():
        ast.parse(src)
    # a flattened subgraph id keeps its string while the function name is sanitized
    assert '@node("investigate:gather_logs")' in files["nodes.py"]
    assert "def investigate_gather_logs(state):" in files["nodes.py"]
    # Send / Command conditional edges without a router mapping degrade to TODO markers
    assert "# TODO: conditional edge" in files["graph.py"]


def test_importing_scaffold_pulls_in_no_framework():
    snippet = (
        "import sys, lg2m.scaffold; "
        "assert 'langgraph' not in sys.modules, 'scaffold imported langgraph'; "
        "assert 'langchain_core' not in sys.modules, 'scaffold imported langchain_core'"
    )
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- golden round-trip (markdown -> code -> introspect -> IR) -----------------


@pytest.mark.langgraph
def test_golden_doc_to_code_to_ir(mini_md_text, tmp_path):
    doc = _doc_model(mini_md_text)
    code = introspect_generated(generate_code(doc), tmp_path, "mini_pipeline")
    assert structural_key(code) == structural_key(doc)
