"""
Role:
- Match the incoming problem description to the most suitable skill.
- Extract coarse task intent such as solve, modify constraints, or debug.

Called by:
- `Operational-Agent.agent`

Calls:
- `skills.loader`
- `knowledge.retrievers.skill_retriever`
"""


def parse_intent(user_input: str) -> dict:
    """Placeholder intent parser."""
    return {"intent": "solve_problem", "matched_skill": "emergency_island_supply"}
