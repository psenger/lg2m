"""The write-only ``lg2m sync`` verb: reconcile free-prose between Markdown and docstrings.

Framework-free, even at runtime: prose lives in source text and Markdown, neither of
which needs a compiled graph. This package must never import a framework, and the AST
reader it leans on never imports the target module.
"""

from __future__ import annotations

from lg2m.sync.engine import SyncResult, run_sync

__all__ = ["SyncResult", "run_sync"]
