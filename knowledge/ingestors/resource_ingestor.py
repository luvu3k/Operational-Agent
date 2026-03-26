"""
Role:
- Ingest raw resource data into the resource knowledge index.

Called by:
- Offline data preparation scripts in the future.

Calls:
- `knowledge.indexes.resources`
"""


def ingest_resources(records: list) -> int:
    """Placeholder resource ingestion."""
    return len(records)
