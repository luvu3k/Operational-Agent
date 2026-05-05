"""
Role:
- Merge user input, selected skill, retrieved resources, and past experience into one structured problem definition.
- Produce the canonical problem object used by later steps.

Called by:
- `Operational-Agent.agent`
- `Operational-Agent.recovery`

Calls:
- `schemas.problem`
- `knowledge.retrievers.resource_retriever`
- `knowledge.retrievers.experience_retriever`
"""


def build_problem_spec(user_input: str, intent_result: dict) -> dict:
    """Placeholder structured problem builder."""
    return {"user_input": user_input, "intent_result": intent_result}
