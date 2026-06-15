"""Shared harness for the scaffold/gen golden round-trips (framework-touching).

``introspect_generated`` writes a generated ``{filename: source}`` package to disk, imports +
compiles it, introspects the real compiled graph, and assembles the code-side ``GraphModel`` --
the same chain ``pipeline.check`` uses. It imports langgraph, so every caller must be marked
``@pytest.mark.langgraph``. ``structural_key`` is the identity-only view both directions assert
on (it ignores prose / loc / meta / a model's ``style``, which the doc legitimately cannot know).

Named ``_roundtrip`` (not ``test_*``) so pytest does not collect it.
"""

from __future__ import annotations

import importlib
import itertools
import sys
from pathlib import Path

from lg2m.annotations.registry import get_registry
from lg2m.diff.assemble import assemble_code_model
from lg2m.ir import GraphModel
from lg2m.pipeline import gather_annotations

_counter = itertools.count()


def write_package(files: dict[str, str], root: Path, pkg_name: str) -> Path:
    pkg = root / pkg_name
    pkg.mkdir(parents=True, exist_ok=True)
    for name, src in files.items():
        (pkg / name).write_text(src, encoding="utf-8")
    return pkg


def introspect_generated(files: dict[str, str], root: Path, graph_id: str) -> GraphModel:
    """Compile + introspect a generated package into a code-side ``GraphModel``.

    Uses a unique package name per call so importlib's module cache never returns a stale build.
    """
    pkg_name = f"lg2m_gen_{next(_counter)}"
    pkg = write_package(files, root, pkg_name)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    module = importlib.import_module(pkg_name)
    compiled = module.build_graph()

    from lg2m.introspect.langgraph_adapter import LangGraphIntrospector  # lazy: framework import

    topology = LangGraphIntrospector(
        compiled, xray=True, registry=get_registry()
    ).introspect(graph_id)
    registry, locations = gather_annotations(pkg)
    return assemble_code_model(topology, registry, locations)


def structural_key(gm: GraphModel) -> dict:
    """Identity-only view: nodes (+kind), edges, routes, predicates, state model, models."""
    return {
        "nodes": {nid: n.kind for nid, n in gm.nodes.items()},
        "edges": sorted((e.src_id, e.dst_id, e.predicate) for e in gm.edges),
        "routes": {s: (r.branches, r.else_target) for s, r in gm.routes.items()},
        "predicates": sorted(gm.predicates),
        "state_model": gm.state_model_name,
        "models": {
            name: (
                dm.is_graph_state,
                tuple((a.name, a.type_str, a.reducer) for a in dm.attributes),
            )
            for name, dm in gm.models.items()
        },
    }
