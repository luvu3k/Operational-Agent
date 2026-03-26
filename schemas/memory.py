"""
Role:
- Define memory record schemas for short-term and long-term use.

Called by:
- `memory.short_term`
- `memory.long_term`
- `memory.summarizer`
"""

from dataclasses import dataclass


@dataclass
class MemoryRecord:
    record_id: str
    content: str
    record_type: str
