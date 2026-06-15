"""lg2m report layer: the DriftReport model and its text/json renderers.

Framework-free and pure: ``model`` is the value object the diff engine fills,
``text`` and ``json`` are total functions from a ``DriftReport`` to a string.
"""

from lg2m.report.json import render_json
from lg2m.report.model import DriftItem, DriftReport
from lg2m.report.text import render_text

__all__ = ["DriftItem", "DriftReport", "render_json", "render_text"]
