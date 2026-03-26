"""
Role:
- Ingest summarized historical cases and debugging lessons into the experience index.

Called by:
- `memory.summarizer`
- Offline data preparation scripts in the future.

Calls:
- `knowledge.indexes.experiences`
"""


def ingest_experiences(records: list) -> int:
    """Placeholder experience ingestion."""
    return len(records)
