"""lg2m introspection seam: the ``GraphIntrospector`` port and the framework-free Fake.

The real langgraph adapter is a later layer and is intentionally NOT imported here,
so importing ``lg2m.introspect`` pulls in no framework.
"""

from lg2m.introspect.base import FakeIntrospector, GraphIntrospector

__all__ = ["FakeIntrospector", "GraphIntrospector"]
