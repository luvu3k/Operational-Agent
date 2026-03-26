"""
Role:
- Agent-facing tool for exact optimization solving.
- Orchestrates exact code generation, execution, and result packaging.

Called by:
- `Operational-Agent.react_loop`

Calls:
- `solver.codegen.exact_generator`
- `solver.sandbox.runner`
- `solver.postprocess.parser`
"""


def run_exact_solver(problem_spec: dict) -> dict:
    """Placeholder exact solver tool."""
    return {"mode": "exact", "problem_spec": problem_spec}
