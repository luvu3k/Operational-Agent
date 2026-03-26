"""
Role:
- Provide shared logging configuration for the project.
- Keeps logging setup out of orchestration and tool logic.

Called by:
- `main.py`
- `Operational-Agent.agent`
- `solver.sandbox.runner`
"""

import logging


def setup_logging() -> None:
    """Configure a simple default logger."""
    logging.basicConfig(level=logging.INFO)
