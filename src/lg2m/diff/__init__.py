"""lg2m diff layer: reconcile topology + annotations + the Markdown contract.

``categories`` holds the drift vocabulary, ``assemble`` builds the two comparable
``GraphModel`` sides, and ``engine`` compares them into a ``DriftReport``. The
orchestration helper that wires parse -> assemble -> reconcile lives in ``engine``.
"""
