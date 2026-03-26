"""
Role:
- Parse raw solver output into a normalized solution structure.

Called by:
- `tools.heuristic_solver_tool`
- `tools.exact_solver_tool`
- `tools.visualization_tool`

Calls:
- `schemas.solution`
"""


def parse_solution(raw_output: dict) -> dict:
    """Placeholder solution parser."""
    return {"parsed_solution": raw_output}
