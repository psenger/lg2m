"""lg2m public surface.

Re-exports the intermediate-representation types and the authoring API (the
metadata-only decorators and the Model-A router). Importing lg2m pulls in no
framework: the annotation layer is framework-free, and the LangGraph introspector
lives behind the optional ``[langgraph]`` extra.
"""

from lg2m.annotations.decorators import data_model, node, predicate, state_model
from lg2m.annotations.router import ELSE, router
from lg2m.ir import (
    Attribute,
    DataModel,
    Diagnostic,
    DiagnosticKind,
    Edge,
    GraphModel,
    Meta,
    MetaKind,
    Node,
    NodeKind,
    Predicate,
    Route,
    SourceLocation,
)

__all__ = [
    # authoring API
    "ELSE",
    "data_model",
    "node",
    "predicate",
    "router",
    "state_model",
    # intermediate representation
    "Attribute",
    "DataModel",
    "Diagnostic",
    "DiagnosticKind",
    "Edge",
    "GraphModel",
    "Meta",
    "MetaKind",
    "Node",
    "NodeKind",
    "Predicate",
    "Route",
    "SourceLocation",
]
