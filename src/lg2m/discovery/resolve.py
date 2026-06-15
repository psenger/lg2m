"""Resolve a ``[tool.lg2m.graphs.<id>]`` config entry into a ``ResolvedGraph``
(docs/design.md Section 5).

Turns the raw config dict (from ``config.loader.load``) into a typed, path-resolved value: the
``module``/``attr`` split of ``graph = "module:callable"``, and the ``markdown`` / ``sys_path``
entries resolved to absolute paths against the config file's directory. Framework-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """A graph config entry is missing or malformed (the CLI maps this to exit code 2)."""


@dataclass(frozen=True)
class ResolvedGraph:
    graph_id: str
    module: str
    attr: str
    markdown_path: Path
    sys_paths: tuple[Path, ...]
    xray: bool
    framework: str


def resolve(cfg: dict[str, Any], *, base_dir: Path, graph_id: str) -> ResolvedGraph:
    graph = cfg.get("graph")
    if not isinstance(graph, str) or ":" not in graph:
        raise ConfigError(
            f"graph {graph_id!r} needs graph = 'module:callable', got {graph!r}"
        )
    module, _, attr = graph.partition(":")
    if not module.strip() or not attr.strip():
        raise ConfigError(f"graph {graph_id!r} has an empty module or callable in {graph!r}")

    markdown = cfg.get("markdown")
    if not isinstance(markdown, str) or not markdown:
        raise ConfigError(f"graph {graph_id!r} needs a markdown path")

    base = Path(base_dir)
    return ResolvedGraph(
        graph_id=graph_id,
        module=module.strip(),
        attr=attr.strip(),
        markdown_path=(base / markdown).resolve(),
        sys_paths=tuple((base / p).resolve() for p in cfg.get("sys_path", [])),
        xray=bool(cfg.get("xray", True)),
        framework=str(cfg.get("framework", "langgraph")),
    )
