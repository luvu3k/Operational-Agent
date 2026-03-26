"""
Role:
- Send prompts to the model and return normalized outputs.
- Hide the differences between future response styles from upper layers.

Called by:
- `Operational-Agent.react_loop`
- `tools.code_repair_tool`
- `solver.codegen.heuristic_generator`
- `solver.codegen.exact_generator`

Calls:
- `llm.client`
"""


def generate_response(prompt: str) -> str:
    """Placeholder model call."""
    return f"MODEL_RESPONSE_PLACEHOLDER: {prompt}"
