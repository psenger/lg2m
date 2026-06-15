"""Load lg2m graph configuration from a ``pyproject.toml`` or ``lg2m.toml``.

Both files key the configuration under the same table path,
``[tool.lg2m.graphs.<id>]``, so a ``pyproject.toml`` section and a standalone
``lg2m.toml`` with the same content yield identical mappings.

TOML reading uses the stdlib ``tomllib`` (Python 3.11+) and falls back to the
``tomli`` backport on Python 3.10 (declared as a conditional dependency in
``pyproject.toml``). ``tomllib.load`` requires a binary file object, so the file
is opened in binary mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib  # API-compatible backport


def load(path: str | Path) -> dict[str, dict[str, Any]]:
    """Return the ``[tool.lg2m.graphs.*]`` mapping from a TOML file.

    Reads a ``pyproject.toml`` or a standalone ``lg2m.toml`` (both keyed under
    ``tool.lg2m.graphs``). Returns ``{}`` when the section is absent. Each graph
    entry is shallow-copied so callers cannot mutate the parsed document.
    """
    data = _read_toml(Path(path))
    graphs = data.get("tool", {}).get("lg2m", {}).get("graphs", {})
    return {graph_id: dict(cfg) for graph_id, cfg in graphs.items()}


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:  # tomllib.load requires a binary file object
        return tomllib.load(fh)
