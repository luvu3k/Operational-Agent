"""
Role:
- Central settings module for model, storage, and solver configuration.
- Avoids hard-coded paths and model names across the codebase.

Called by:
- `llm.client`
- `Operational-Agent.agent`
- `memory.store`
- `solver.sandbox.executor`
"""

from dataclasses import dataclass


@dataclass
class Settings:
    model_name: str = "gpt-5"
    storage_dir: str = "storage"
    runs_dir: str = "storage/runs"


def get_settings() -> Settings:
    """Return default settings."""
    return Settings()
