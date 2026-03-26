"""
Role:
- Load skill Markdown and metadata into memory for matching and prompting.
- Provide a simple interface for selecting and reading skill content.

Called by:
- `Operational-Agent.intent_parser`
- `knowledge.retrievers.skill_retriever`
"""


def load_skill(skill_name: str) -> dict:
    """Placeholder skill loader."""
    return {"skill_name": skill_name}
