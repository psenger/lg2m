"""Framework-free code/markdown generation for ``lg2m gen`` (docs/design.md Section 10).

``scaffold`` emits *text*: annotated LangGraph source (``--from-doc``) and the Markdown
contract skeleton (``--from-code``). Importing it pulls in **no** framework; the generated
code imports LangGraph, but this package never does. The ``--from-code`` direction reaches the
real graph only through the CLI's reuse of the existing (lazy) introspect chain, not from here.
"""

from __future__ import annotations

from lg2m.scaffold.generate import GENERATED_FILES, ScaffoldError, generate_code
from lg2m.scaffold.markdown import generate_markdown

__all__ = ["GENERATED_FILES", "ScaffoldError", "generate_code", "generate_markdown"]
