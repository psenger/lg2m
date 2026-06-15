"""Import the user's graph factory and run it — the untrusted-code boundary
(docs/design.md Section 12).

``check`` runs user code: it prepends the configured ``sys_path`` roots, imports the module (which
imports the framework and, as a side effect, populates the lg2m annotation registry as the
decorators run), and calls the factory to obtain the compiled graph. Any failure — a bad module, a
missing callable, or an exception from the factory — is captured as an ``IMPORT_FAILURE`` diagnostic
rather than raised, so the caller can report it like any other drift. This module imports no
framework itself; the user's module is what pulls langgraph in.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass, field
from typing import Any

from lg2m.discovery.resolve import ResolvedGraph
from lg2m.ir import Diagnostic, DiagnosticKind, SourceLocation


@dataclass
class LoadedGraph:
    compiled: Any | None
    diagnostics: list[Diagnostic] = field(default_factory=list)


def load_compiled(resolved: ResolvedGraph) -> LoadedGraph:
    for path in resolved.sys_paths:
        entry = str(path)
        if entry not in sys.path:
            sys.path.insert(0, entry)
    try:
        module = importlib.import_module(resolved.module)
        compiled = getattr(module, resolved.attr)()
    except Exception as exc:  # untrusted user code: never let it escape
        diag = Diagnostic(
            kind=DiagnosticKind.IMPORT_FAILURE,
            subject=resolved.graph_id,
            message=f"failed to load {resolved.module}:{resolved.attr}: {exc!r}",
            loc=SourceLocation(f"{resolved.module}:{resolved.attr}", 0),
        )
        return LoadedGraph(compiled=None, diagnostics=[diag])
    return LoadedGraph(compiled=compiled)
