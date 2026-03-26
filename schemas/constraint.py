"""
Role:
- Define the normalized representation of a constraint.

Called by:
- `Operational-Agent.problem_builder`
- `tools.validator_tool`
"""

from dataclasses import dataclass


@dataclass
class ConstraintSpec:
    name: str
    expression: str
